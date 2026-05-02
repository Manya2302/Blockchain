"""TAP-DEV Phase 2+ — Evidence Views with notifications, IPFS, blockchain, self-destructing docs"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Evidence
from .forms import EvidenceUploadForm
from .expiry_engine import ExpiryEngine
from apps.events.engine import EventChainEngine
from apps.analysis.detector import AnomalyDetector
from apps.analysis.scoring import TrustScorer
from apps.notifications.models import Notification
from apps.users.utils import log_activity


def analyst_or_admin(user):
    return hasattr(user,'profile') and user.profile.role in ('ANALYST','ADMIN')


def _notify_analyst(evidence, title, message, notif_type='INFO'):
    from django.contrib.auth.models import User
    analysts = User.objects.filter(profile__role__in=['ANALYST','ADMIN'])
    for a in analysts:
        Notification.objects.create(user=a, title=title, message=message,
                                    notif_type=notif_type, link=f'/evidence/{evidence.pk}/')


@login_required
def upload_view(request):
    form = EvidenceUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        evidence = form.save(commit=False)
        f = request.FILES['file']
        evidence.sha256_hash      = Evidence.compute_sha256(f)
        evidence.uploader         = request.user
        evidence.filename_original = f.name
        evidence.file_size        = f.size
        evidence.mime_type        = f.content_type or 'application/octet-stream'

        # Self-destructing document: expiry policy
        expiry_enabled = form.cleaned_data.get('expiry_enabled', False)
        if expiry_enabled:
            evidence.expiry_enabled = True
            expiry_type = form.cleaned_data.get('expiry_type', 'NONE')
            evidence.expiry_type = expiry_type

            if expiry_type == 'TIMED':
                expiry_hours = form.cleaned_data.get('expiry_hours')
                expiry_date = form.cleaned_data.get('expiry_date')
                if expiry_hours:
                    evidence.expires_at = timezone.now() + timezone.timedelta(hours=expiry_hours)
                elif expiry_date:
                    evidence.expires_at = expiry_date

        evidence.save()

        engine = EventChainEngine(evidence)
        engine.create_event('UPLOAD', request.user, f'Initial upload: {f.name} ({evidence.file_size_display})')

        # Create expiry event if enabled
        if evidence.expiry_enabled and evidence.expires_at:
            engine.create_event(
                'EXPIRE_SET', request.user,
                f'Self-destruct policy set: expires {evidence.expires_at.strftime("%Y-%m-%d %H:%M")} UTC',
                metadata={'expires_at': evidence.expires_at.isoformat()}
            )

        AnomalyDetector(evidence).run()
        TrustScorer(evidence).recalculate()

        log_activity(request.user, 'EVIDENCE_UPLOAD', 'EVIDENCE',
                     f"Uploaded: {evidence.title}", request=request)
        notif_msg = f'"{evidence.title}" submitted. Trust score: {evidence.trust_score}/100.'
        if evidence.expiry_enabled:
            notif_msg += f' Self-destruct: {evidence.expires_at.strftime("%Y-%m-%d %H:%M") if evidence.expires_at else "event-based"}.'
        Notification.objects.create(
            user=request.user, title='Evidence Uploaded',
            message=notif_msg, notif_type='SUCCESS', link=f'/evidence/{evidence.pk}/'
        )
        _notify_analyst(evidence, 'New Evidence Submitted',
                        f'{request.user.username} submitted "{evidence.title}".', 'INFO')

        messages.success(request, f'Evidence uploaded. SHA-256: {evidence.sha256_hash[:16]}…')
        return redirect('evidence:detail', pk=evidence.pk)
    return render(request, 'evidence/upload.html', {'form': form})


@login_required
def detail_view(request, pk):
    ev = get_object_or_404(Evidence, pk=pk)
    if not analyst_or_admin(request.user) and ev.uploader != request.user:
        messages.error(request,'Access denied.')
        return redirect('dashboard:home')

    # Check and process expiry
    expiry_engine = ExpiryEngine(ev)
    expiry_engine.check_and_expire()
    ev.refresh_from_db()

    expiry_status = expiry_engine.get_expiry_status()

    events    = ev.events.select_related('actor','previous_event').order_by('timestamp')
    anomalies = ev.anomalies.order_by('-detected_at')
    versions  = ev.get_all_versions()
    from apps.blockchain.models import BlockchainTransaction, IPFSRecord
    txs       = ev.blockchain_txs.order_by('-anchored_at')[:5]
    engine    = EventChainEngine(ev)
    chain_valid, broken_at = engine.verify_full_chain()
    return render(request, 'evidence/detail.html', {
        'ev': ev, 'events': events, 'anomalies': anomalies,
        'versions': versions, 'txs': txs,
        'chain_valid': chain_valid, 'broken_at': broken_at,
        'can_edit': analyst_or_admin(request.user) or ev.uploader == request.user,
        'is_analyst': analyst_or_admin(request.user),
        'expiry_status': expiry_status,
    })


@login_required
def list_view(request):
    if analyst_or_admin(request.user): qs = Evidence.objects.select_related('uploader').filter(is_latest_version=True)
    else: qs = Evidence.objects.filter(uploader=request.user, is_latest_version=True)
    status = request.GET.get('status','')
    trust  = request.GET.get('trust','')
    search = request.GET.get('q','')
    expiry_filter = request.GET.get('expiry', '')
    if status: qs = qs.filter(status=status)
    if trust == 'low':    qs = qs.filter(trust_score__lt=50)
    if trust == 'medium': qs = qs.filter(trust_score__gte=50, trust_score__lt=80)
    if trust == 'high':   qs = qs.filter(trust_score__gte=80)
    if search: qs = qs.filter(title__icontains=search)
    if expiry_filter == 'active': qs = qs.filter(expiry_enabled=True, is_expired=False)
    if expiry_filter == 'expired': qs = qs.filter(is_expired=True)
    if expiry_filter == 'no_expiry': qs = qs.filter(expiry_enabled=False)

    return render(request, 'evidence/list.html', {
        'evidences': qs, 'status': status, 'trust': trust, 'search': search,
        'status_choices': Evidence.STATUS_CHOICES, 'expiry_filter': expiry_filter,
    })


@login_required
def add_event_view(request, pk):
    ev = get_object_or_404(Evidence, pk=pk)
    if not analyst_or_admin(request.user) and ev.uploader != request.user:
        messages.error(request,'Access denied.')
        return redirect('dashboard:home')

    # Block events on expired documents
    if ev.is_expired:
        messages.error(request, 'Cannot add events to expired documents.')
        return redirect('evidence:detail', pk=pk)

    allowed = ['MODIFY','VERIFY','STORE','FLAG','NOTE']
    if request.method == 'POST':
        et   = request.POST.get('event_type','').upper()
        desc = request.POST.get('description','').strip()
        if et not in allowed:
            messages.error(request,'Invalid event type.')
            return redirect('evidence:detail', pk=pk)
        engine = EventChainEngine(ev)
        engine.create_event(et, request.user, desc)
        AnomalyDetector(ev).run()
        TrustScorer(ev).recalculate()
        status_map = {'VERIFY':'VERIFIED','STORE':'STORED','FLAG':'FLAGGED'}
        if et in status_map:
            ev.status = status_map[et]; ev.save(update_fields=['status'])
        log_activity(request.user, f'EVENT_{et}', 'EVIDENCE', f"Evidence #{pk}", request=request)
        # Notify uploader
        if et == 'VERIFY':
            Notification.objects.create(user=ev.uploader, title='Evidence Verified',
                message=f'"{ev.title}" has been verified by {request.user.username}.',
                notif_type='SUCCESS', link=f'/evidence/{pk}/')
        elif et == 'FLAG':
            Notification.objects.create(user=ev.uploader, title='Evidence Flagged',
                message=f'"{ev.title}" has been flagged: {desc[:60]}',
                notif_type='WARNING', link=f'/evidence/{pk}/')
        messages.success(request, f'{et} event appended to chain.')
    return redirect('evidence:detail', pk=pk)


@login_required
def set_expiry_view(request, pk):
    """Set or update expiry policy on an evidence item."""
    ev = get_object_or_404(Evidence, pk=pk)
    if not analyst_or_admin(request.user) and ev.uploader != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    if ev.is_expired:
        messages.error(request, 'Document is already expired.')
        return redirect('evidence:detail', pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', 'set')

        if action == 'remove':
            ev.expiry_enabled = False
            ev.expiry_type = 'NONE'
            ev.expires_at = None
            ev.expiry_condition = ''
            ev.save(update_fields=['expiry_enabled', 'expiry_type', 'expires_at', 'expiry_condition'])
            messages.success(request, 'Expiry policy removed.')
            log_activity(request.user, 'EXPIRY_REMOVED', 'EVIDENCE',
                         f'Removed expiry from: {ev.title}', request=request)
        else:
            expiry_hours = request.POST.get('expiry_hours', '')
            expiry_date = request.POST.get('expiry_date', '')

            if expiry_hours:
                try:
                    hours = int(expiry_hours)
                    ev.expiry_enabled = True
                    ev.expiry_type = 'TIMED'
                    ev.expires_at = timezone.now() + timezone.timedelta(hours=hours)
                    ev.save(update_fields=['expiry_enabled', 'expiry_type', 'expires_at'])

                    engine = EventChainEngine(ev)
                    engine.create_event('EXPIRE_SET', request.user,
                                        f'Self-destruct updated: expires in {hours} hours')
                    messages.success(request, f'Expiry set: {hours} hours from now.')
                except (ValueError, TypeError):
                    messages.error(request, 'Invalid hours value.')
            elif expiry_date:
                try:
                    from django.utils.dateparse import parse_datetime
                    dt = parse_datetime(expiry_date)
                    if dt:
                        ev.expiry_enabled = True
                        ev.expiry_type = 'TIMED'
                        ev.expires_at = dt
                        ev.save(update_fields=['expiry_enabled', 'expiry_type', 'expires_at'])
                        messages.success(request, f'Expiry set: {dt.strftime("%Y-%m-%d %H:%M")}.')
                    else:
                        messages.error(request, 'Invalid date format.')
                except Exception:
                    messages.error(request, 'Invalid date.')

        return redirect('evidence:detail', pk=pk)

    return render(request, 'evidence/set_expiry.html', {'ev': ev})


@login_required
def delete_view(request, pk):
    ev = get_object_or_404(Evidence, pk=pk)
    if not analyst_or_admin(request.user) and ev.uploader != request.user:
        messages.error(request,'Access denied.')
        return redirect('dashboard:home')
    if request.method == 'POST':
        title = ev.title
        if ev.file: ev.file.delete(save=False)
        ev.delete()
        log_activity(request.user, 'EVIDENCE_DELETE', 'EVIDENCE', f"Deleted: {title}", request=request)
        messages.success(request, f'Evidence "{title}" deleted.')
        return redirect('evidence:list')
    return render(request, 'evidence/confirm_delete.html', {'ev': ev})

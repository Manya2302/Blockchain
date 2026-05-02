"""TAP-DEV Phase 3+ — Evolution Tracker Views (Enhanced)"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import DocumentVersion, EvolutionAIAnalysis
from .comparator import DocumentComparator
from .ai_engine import EvolutionAIEngine


def require_analyst(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
        if role not in ('ANALYST', 'ADMIN'):
            messages.error(request, 'Analyst or Admin access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_analyst
def tracker_dashboard(request):
    """Evolution tracker overview with AI analysis stats."""
    from apps.evidence.models import Evidence
    # Evidences with versions
    versioned = Evidence.objects.filter(
        parent_evidence__isnull=False
    ).select_related('parent_evidence', 'uploader').order_by('-created_at')[:20]
    recent_comparisons = DocumentVersion.objects.select_related(
        'evidence', 'compared_to'
    ).order_by('-analyzed_at')[:10]
    forged_count = DocumentVersion.objects.filter(
        change_type__in=['FORGED', 'CRITICAL']
    ).count()

    # AI analysis stats
    ai_analyses = EvolutionAIAnalysis.objects.order_by('-analyzed_at')[:10]
    critical_count = EvolutionAIAnalysis.objects.filter(risk_level='CRITICAL').count()
    high_count = EvolutionAIAnalysis.objects.filter(risk_level='HIGH').count()

    return render(request, 'evolution_tracker/dashboard.html', {
        'versioned_evidence': versioned,
        'recent_comparisons': recent_comparisons,
        'forged_count': forged_count,
        'ai_analyses': ai_analyses,
        'critical_count': critical_count,
        'high_count': high_count,
    })


@require_analyst
def compare_versions(request, evidence_id):
    """Compare an evidence version with its parent."""
    from apps.evidence.models import Evidence

    ev2 = get_object_or_404(Evidence, id=evidence_id)
    ev1 = ev2.parent_evidence

    if not ev1:
        messages.warning(request, "No parent version to compare with.")
        return redirect('evidence:detail', pk=evidence_id)

    # Run comparison
    comparator = DocumentComparator(ev1, ev2)
    result = comparator.analyze()

    # Save result
    doc_version, _ = DocumentVersion.objects.update_or_create(
        evidence=ev2,
        compared_to=ev1,
        defaults={
            'version_number': ev2.version,
            'text_similarity': result['text_similarity'],
            'words_added': result['words_added'],
            'words_removed': result['words_removed'],
            'chars_changed': result['chars_changed'],
            'file_size_delta': result['file_size_delta'],
            'hash_changed': result['hash_changed'],
            'fraud_score': result['fraud_score'],
            'fraud_signals': result['fraud_signals'],
            'change_type': result['change_type'],
            'diff_summary': result['diff_summary'],
        }
    )

    return render(request, 'evolution_tracker/compare.html', {
        'ev1': ev1,
        'ev2': ev2,
        'doc_version': doc_version,
        'result': result,
    })


@require_analyst
def version_timeline(request, evidence_id):
    """Full version evolution timeline with AI analysis for an evidence chain."""
    from apps.evidence.models import Evidence

    evidence = get_object_or_404(Evidence, id=evidence_id)
    versions = list(evidence.get_all_versions())

    # Get all comparisons for this chain
    version_ids = [v.pk for v in versions]
    comparisons = DocumentVersion.objects.filter(
        evidence_id__in=version_ids
    ).select_related('evidence', 'compared_to').order_by('version_number')

    # Get latest AI analysis
    ai_analysis = EvolutionAIAnalysis.objects.filter(
        evidence_id__in=version_ids
    ).order_by('-analyzed_at').first()

    # Build timeline data
    timeline_items = []
    for v in versions:
        comp = comparisons.filter(evidence=v).first()
        timeline_items.append({
            'evidence': v,
            'comparison': comp,
            'is_current': v.pk == evidence.pk,
        })

    return render(request, 'evolution_tracker/timeline.html', {
        'evidence': evidence,
        'versions': versions,
        'timeline_items': timeline_items,
        'ai_analysis': ai_analysis,
        'comparisons': comparisons,
    })


@require_analyst
def run_ai_analysis(request, evidence_id):
    """Run full AI evolution analysis on an evidence chain."""
    from apps.evidence.models import Evidence
    from apps.notifications.models import Notification
    from apps.users.utils import log_activity

    evidence = get_object_or_404(Evidence, id=evidence_id)

    # First, ensure all versions are compared
    versions = list(evidence.get_all_versions())
    for i in range(1, len(versions)):
        ev1, ev2 = versions[i - 1], versions[i]
        if not DocumentVersion.objects.filter(evidence=ev2, compared_to=ev1).exists():
            comparator = DocumentComparator(ev1, ev2)
            result = comparator.analyze()
            DocumentVersion.objects.create(
                evidence=ev2, compared_to=ev1,
                version_number=ev2.version,
                text_similarity=result['text_similarity'],
                words_added=result['words_added'],
                words_removed=result['words_removed'],
                chars_changed=result['chars_changed'],
                file_size_delta=result['file_size_delta'],
                hash_changed=result['hash_changed'],
                fraud_score=result['fraud_score'],
                fraud_signals=result['fraud_signals'],
                change_type=result['change_type'],
                diff_summary=result['diff_summary'],
            )

    # Run AI analysis
    engine = EvolutionAIEngine(evidence)
    ai_result = engine.analyze_full_chain()

    # Save AI analysis
    analysis = EvolutionAIAnalysis.objects.create(
        evidence=evidence,
        analyzed_by=request.user,
        anomaly_score=ai_result['anomaly_score'],
        risk_level=ai_result['risk_level'],
        features=ai_result['features'],
        patterns=ai_result['patterns'],
        version_count=ai_result['version_count'],
        comparison_count=ai_result['comparison_count'],
        chain_span_days=ai_result['chain_span_days'],
        summary=ai_result['summary'],
    )

    # Log and notify
    log_activity(request.user, 'EVOLUTION_AI_SCAN', 'ANALYSIS',
                 f"AI evolution analysis on '{evidence.title}': {ai_result['risk_level']}",
                 request=request)

    if ai_result['risk_level'] in ('HIGH', 'CRITICAL'):
        # Notify all analysts
        from django.contrib.auth.models import User
        analysts = User.objects.filter(profile__role__in=['ANALYST', 'ADMIN'])
        for analyst in analysts:
            Notification.objects.create(
                user=analyst,
                title=f"🚨 {ai_result['risk_level']} Risk: Document Evolution Alert",
                message=f"AI detected {ai_result['risk_level'].lower()} risk tampering patterns "
                        f"in '{evidence.title}' ({len(ai_result['patterns'])} patterns found).",
                notif_type='WARNING' if ai_result['risk_level'] == 'HIGH' else 'ALERT',
                link=f'/evolution/timeline/{evidence.pk}/',
            )

    messages.success(request,
                     f"AI Evolution Analysis complete: {ai_result['risk_level']} risk "
                     f"({analysis.anomaly_percent}% anomaly score)")
    return redirect('evolution:timeline', evidence_id=evidence.pk)


@require_analyst
def ai_analysis_detail(request, analysis_id):
    """View detailed AI analysis results."""
    analysis = get_object_or_404(EvolutionAIAnalysis, id=analysis_id)
    return render(request, 'evolution_tracker/ai_detail.html', {
        'analysis': analysis,
    })

"""TAP-DEV Blockchain Views — anchor evidence, view transactions"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.evidence.models import Evidence
from .models import BlockchainTransaction, IPFSRecord
from .simulator import BlockchainSimulator, IPFSSimulator
from apps.users.utils import log_activity


def analyst_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user,'profile') or request.user.profile.role not in ('ANALYST','ADMIN'):
            messages.error(request,'Analyst access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def anchor_view(request, pk):
    ev = get_object_or_404(Evidence, pk=pk)
    if request.method == 'POST':
        sim = BlockchainSimulator()
        tx  = sim.anchor_evidence(ev, user=request.user)
        # Also pin to IPFS simulation
        ipfs = IPFSSimulator()
        ipfs.pin_evidence(ev)
        log_activity(request.user,'BLOCKCHAIN_ANCHOR','BLOCKCHAIN',
                     f"Evidence #{pk} anchored: {tx.tx_hash[:20]}…", request=request)
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=ev.uploader, title='Evidence Blockchain Anchored',
            message=f'"{ev.title}" has been anchored on {tx.network}. TX: {tx.tx_hash[:20]}…',
            notif_type='SUCCESS', link=f'/evidence/{ev.pk}/'
        )
        messages.success(request, f'Anchored on blockchain. TX: {tx.tx_hash[:20]}…')
    return redirect('evidence:detail', pk=pk)


@analyst_required
def tx_list(request):
    txs = BlockchainTransaction.objects.select_related('evidence','submitter').all()[:50]
    stats = {'total': txs.count(), 'confirmed': BlockchainTransaction.objects.filter(status='CONFIRMED').count()}
    return render(request, 'blockchain/tx_list.html', {'txs': txs, 'stats': stats})

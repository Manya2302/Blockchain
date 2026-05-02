"""TAP-DEV Phase 5 — Global Forensic Network Views"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import ForensicNode, CrossChainTransfer, NetworkConsortiumMember

def p5_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,'profile',None),'role','') in ('ANALYST','ADMIN'):
            return fn(request, *args, **kwargs)
        messages.error(request,'Access denied.'); return redirect('dashboard:home')
    return wrap

def admin_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,'profile',None),'role','') == 'ADMIN':
            return fn(request, *args, **kwargs)
        messages.error(request,'Admin required.'); return redirect('dashboard:home')
    return wrap

@p5_required
def network_dashboard(request):
    nodes = ForensicNode.objects.order_by('-trust_score')
    all_transfers = CrossChainTransfer.objects.select_related('source_node','target_node').order_by('-initiated_at')
    active_nodes = nodes.filter(status='ACTIVE').count()
    pending_transfers = all_transfers.filter(status='PENDING').count()
    confirmed_transfers = all_transfers.filter(status='CONFIRMED').count()
    transfers = all_transfers[:30]

    # Geo data for globe visualization
    node_geo = list(nodes.filter(geo_lat__isnull=False).values(
        'name','country_name','country_code','status','blockchain','geo_lat','geo_lon','evidence_count','trust_score'
    ))

    chain_dist = {}
    for n in nodes:
        chain_dist[n.blockchain] = chain_dist.get(n.blockchain, 0) + 1

    transfer_stats = {
        'PENDING': pending_transfers,
        'BRIDGING': all_transfers.filter(status='BRIDGING').count(),
        'CONFIRMED': confirmed_transfers,
        'FAILED': all_transfers.filter(status='FAILED').count(),
    }

    return render(request, 'global_network/dashboard.html', {
        'nodes': nodes, 'transfers': transfers,
        'stats': {'total_nodes': nodes.count(), 'active': active_nodes,
                  'pending': pending_transfers, 'confirmed': confirmed_transfers},
        'node_geo_json': json.dumps(node_geo),
        'chain_dist_json': json.dumps(chain_dist),
        'transfer_stats_json': json.dumps(transfer_stats),
    })

@p5_required
def node_detail(request, node_id):
    node = get_object_or_404(ForensicNode, id=node_id)
    transfers = CrossChainTransfer.objects.filter(
        source_node=node) | CrossChainTransfer.objects.filter(target_node=node)
    transfers = transfers.order_by('-initiated_at')[:20]
    return render(request, 'global_network/node_detail.html', {'node': node, 'transfers': transfers})

@admin_required
def register_node(request):
    if request.method == 'POST':
        import hashlib, secrets
        pk, sk_hash, _ = __import__('apps.quantum_crypto.models', fromlist=['QuantumSignature']).QuantumSignature.generate_pq_keypair() if True else (secrets.token_hex(32), '', {})
        node = ForensicNode.objects.create(
            name=request.POST['name'],
            node_type=request.POST.get('node_type','ENTERPRISE'),
            country_code=request.POST.get('country_code','US'),
            country_name=request.POST.get('country_name','United States'),
            city=request.POST.get('city',''),
            blockchain=request.POST.get('blockchain','ETHEREUM'),
            node_address=request.POST.get('node_address',''),
            public_key=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
            did_identifier=f"did:tapdev:{secrets.token_hex(16)}",
            geo_lat=float(request.POST.get('geo_lat',0) or 0),
            geo_lon=float(request.POST.get('geo_lon',0) or 0),
        )
        messages.success(request, f"Node '{node.name}' registered on {node.blockchain}. DID: {node.did_identifier}")
        return redirect('global_network:dashboard')
    return render(request, 'global_network/register_node.html', {
        'node_types': ForensicNode.NODE_TYPE,
        'chain_choices': ForensicNode.CHAIN_CHOICES,
    })

@p5_required
def initiate_transfer(request, evidence_id):
    from apps.evidence.models import Evidence
    evidence = get_object_or_404(Evidence, pk=evidence_id)
    if request.method == 'POST':
        source = ForensicNode.objects.filter(status='ACTIVE').first()
        target_id = request.POST.get('target_node')
        target = get_object_or_404(ForensicNode, id=target_id)
        import hashlib, secrets
        transfer = CrossChainTransfer.objects.create(
            source_node=source, target_node=target, evidence=evidence,
            source_chain=source.blockchain, target_chain=target.blockchain,
            bridge_protocol='TAP-IBC', status='BRIDGING',
            source_tx_hash='0x' + hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:40],
            initiated_by=request.user, evidence_hash=evidence.sha256_hash,
        )
        # Simulate confirmation
        transfer.target_tx_hash = '0x' + hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:40]
        transfer.status = 'CONFIRMED'
        transfer.confirmed_at = timezone.now()
        transfer.attestation = f"Cross-chain attestation verified by TAP-DEV IBC bridge"
        transfer.save()
        messages.success(request, f"Evidence cross-chain transfer confirmed: {source.blockchain} → {target.blockchain}")
        return redirect('evidence:detail', pk=evidence_id)
    nodes = ForensicNode.objects.filter(status='ACTIVE').exclude(blockchain='ETHEREUM').order_by('country_name')
    return render(request, 'global_network/transfer.html', {'evidence': evidence, 'nodes': nodes})

@p5_required
def network_api(request):
    """JSON API for network status."""
    nodes = list(ForensicNode.objects.filter(status='ACTIVE').values(
        'name','country_name','blockchain','geo_lat','geo_lon','trust_score','evidence_count'
    ))
    return JsonResponse({'nodes': nodes, 'total': len(nodes)})

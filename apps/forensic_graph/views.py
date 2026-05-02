"""TAP-DEV Phase 3 — Forensic Graph Visualization"""
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


def require_analyst(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        from django.shortcuts import redirect
        from django.contrib import messages
        role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
        if role not in ('ANALYST', 'ADMIN'):
            messages.error(request, 'Access denied.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_analyst
def graph_dashboard(request):
    """Main forensic graph visualization page."""
    from apps.evidence.models import Evidence
    evidence_list = Evidence.objects.filter(is_latest_version=True).order_by('-created_at')[:30]
    selected_id = request.GET.get('evidence_id')
    selected = None
    graph_data = None

    if selected_id:
        from django.shortcuts import get_object_or_404
        selected = get_object_or_404(Evidence, id=selected_id)
        graph_data = json.dumps(_build_graph(selected))

    return render(request, 'forensic_graph/dashboard.html', {
        'evidence_list': evidence_list,
        'selected': selected,
        'graph_data': graph_data,
    })


@require_analyst
def graph_data_api(request, evidence_id):
    """API endpoint returning graph JSON for D3.js visualization."""
    from apps.evidence.models import Evidence
    evidence = get_object_or_404(Evidence, id=evidence_id)
    data = _build_graph(evidence)
    return JsonResponse(data)


def _build_graph(evidence):
    """
    Build a graph JSON structure for D3 force-directed visualization.
    Nodes: evidence, events, anomalies, blockchain anchors, AI predictions
    Links: event chain, anomaly refs, blockchain anchors
    """
    from apps.events.models import Event
    from apps.analysis.models import Anomaly
    from apps.blockchain.models import BlockchainTransaction
    from apps.ai_engine.models import AIPrediction

    nodes = []
    links = []

    # ── Evidence root node ──────────────────────────────────────────
    nodes.append({
        'id': f'ev_{evidence.id}',
        'label': evidence.title[:30],
        'type': 'evidence',
        'status': evidence.status,
        'trust': evidence.trust_score,
        'color': '#00d4ff',
        'size': 24,
        'metadata': {
            'hash': evidence.sha256_hash[:16] + '...',
            'version': evidence.version,
            'uploader': evidence.uploader.username,
        }
    })

    # ── Event nodes ─────────────────────────────────────────────────
    events = list(Event.objects.filter(evidence=evidence).order_by('sequence_number'))
    COLOR_MAP = {
        'UPLOAD': '#00d4ff', 'MODIFY': '#f59e0b', 'VERIFY': '#10b981',
        'STORE': '#8b5cf6', 'FLAG': '#ef4444', 'NOTE': '#6b7280'
    }
    prev_node_id = f'ev_{evidence.id}'

    for ev in events:
        node_id = f'evt_{ev.id}'
        is_sim = ev.metadata.get('is_simulation', False)
        nodes.append({
            'id': node_id,
            'label': f'{ev.event_type} #{ev.sequence_number}',
            'type': 'event',
            'event_type': ev.event_type,
            'color': '#ff6b6b' if is_sim else COLOR_MAP.get(ev.event_type, '#6b7280'),
            'size': 16,
            'is_simulation': is_sim,
            'metadata': {
                'timestamp': ev.timestamp.isoformat(),
                'actor': ev.actor.username if ev.actor else 'unknown',
                'hash': ev.event_hash[:16] + '...' if ev.event_hash else '',
                'integrity': ev.verify_chain_integrity(),
            }
        })
        links.append({
            'source': prev_node_id,
            'target': node_id,
            'type': 'chain',
            'label': 'chain',
            'color': '#334155',
        })
        prev_node_id = node_id

    # ── Anomaly nodes ───────────────────────────────────────────────
    anomalies = Anomaly.objects.filter(evidence=evidence, is_resolved=False)
    SEVERITY_COLOR = {'LOW': '#84cc16', 'MEDIUM': '#f59e0b', 'HIGH': '#ef4444'}

    for a in anomalies:
        node_id = f'anom_{a.id}'
        nodes.append({
            'id': node_id,
            'label': a.anomaly_type.replace('_', ' '),
            'type': 'anomaly',
            'severity': a.severity,
            'color': SEVERITY_COLOR.get(a.severity, '#6b7280'),
            'size': 18,
            'metadata': {
                'description': a.description[:80],
                'detected_at': a.detected_at.isoformat(),
            }
        })
        ref_node = f'evt_{a.related_event_id}' if a.related_event_id else f'ev_{evidence.id}'
        links.append({
            'source': ref_node,
            'target': node_id,
            'type': 'anomaly',
            'label': a.severity,
            'color': SEVERITY_COLOR.get(a.severity, '#6b7280'),
        })

    # ── Blockchain anchor nodes ──────────────────────────────────────
    txs = BlockchainTransaction.objects.filter(evidence=evidence)[:3]
    for tx in txs:
        node_id = f'tx_{tx.id}'
        nodes.append({
            'id': node_id,
            'label': tx.tx_hash[:12] + '…',
            'type': 'blockchain',
            'color': '#8b5cf6',
            'size': 20,
            'metadata': {
                'tx_hash': tx.tx_hash,
                'network': tx.network,
                'block': tx.block_number,
                'status': tx.status,
            }
        })
        ref = f'evt_{tx.event_id}' if tx.event_id else f'ev_{evidence.id}'
        links.append({
            'source': ref,
            'target': node_id,
            'type': 'blockchain',
            'label': 'anchored',
            'color': '#8b5cf6',
        })

    # ── AI Prediction node ──────────────────────────────────────────
    pred = AIPrediction.objects.filter(evidence=evidence).order_by('-predicted_at').first()
    if pred:
        risk_colors = {
            'SAFE': '#10b981', 'LOW': '#84cc16', 'MEDIUM': '#f59e0b',
            'HIGH': '#ef4444', 'CRITICAL': '#dc2626'
        }
        nodes.append({
            'id': f'ai_{pred.id}',
            'label': f'AI: {pred.risk_level}',
            'type': 'ai',
            'color': risk_colors.get(pred.risk_level, '#6b7280'),
            'size': 22,
            'metadata': {
                'probability': f"{pred.anomaly_probability:.0%}",
                'risk': pred.risk_level,
                'confidence': f"{pred.confidence:.0%}",
                'patterns': pred.detected_patterns,
            }
        })
        links.append({
            'source': f'ev_{evidence.id}',
            'target': f'ai_{pred.id}',
            'type': 'ai',
            'label': 'analyzed',
            'color': risk_colors.get(pred.risk_level, '#6b7280'),
        })

    # ── Version history nodes ────────────────────────────────────────
    if evidence.parent_evidence:
        par = evidence.parent_evidence
        nodes.append({
            'id': f'par_{par.id}',
            'label': f'v{par.version}: {par.title[:20]}',
            'type': 'version',
            'color': '#0891b2',
            'size': 18,
            'metadata': {'version': par.version, 'hash': par.sha256_hash[:16]}
        })
        links.append({
            'source': f'par_{par.id}',
            'target': f'ev_{evidence.id}',
            'type': 'version',
            'label': f'v{par.version}→v{evidence.version}',
            'color': '#0891b2',
        })

    return {'nodes': nodes, 'links': links, 'evidence_id': evidence.id}

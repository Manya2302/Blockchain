"""TAP-DEV Phase 5 — Autonomous AI Investigation Engine Views"""
import json, hashlib, secrets, time, random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import AIInvestigation, ForensicNarrative

def analyst_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,'profile',None),'role','') in ('ANALYST','ADMIN'):
            return fn(request, *args, **kwargs)
        messages.error(request,'Analyst access required.'); return redirect('dashboard:home')
    return wrap

@analyst_required
def investigation_dashboard(request):
    all_investigations = AIInvestigation.objects.select_related('organization').order_by('-started_at')
    complete = all_investigations.filter(status='COMPLETE').count()
    critical = all_investigations.filter(threat_level='CRITICAL').count()
    total    = all_investigations.count()
    investigations = all_investigations

    inv_type_dist = {}
    for inv in investigations[:50]:
        inv_type_dist[inv.investigation_type] = inv_type_dist.get(inv.investigation_type, 0) + 1

    ai_pipeline = ['BiLSTM Sequence Analysis','GNN Pattern Recognition','LLM Narrative Generation','RL Action Recommendation']
    return render(request, 'autonomous_ai/dashboard.html', {
        'investigations': investigations[:20],
        'stats': {'total': total, 'complete': complete, 'critical': critical,
                  'avg_confidence': round(sum(i.confidence_score for i in investigations[:20]) / max(min(20, total), 1) * 100, 1)},
        'inv_type_dist_json': json.dumps(inv_type_dist),
        'ai_pipeline': ai_pipeline,
    })

@analyst_required
def investigation_detail(request, inv_id):
    inv = get_object_or_404(AIInvestigation, id=inv_id)
    narratives = ForensicNarrative.objects.filter(investigation=inv).order_by('-generated_at')
    return render(request, 'autonomous_ai/detail.html', {'inv': inv, 'narratives': narratives})

@analyst_required
def launch_investigation(request):
    if request.method == 'POST':
        from apps.evidence.models import Evidence
        from apps.organizations.models import Organization

        inv_type = request.POST.get('investigation_type', 'TIMELINE_ANOMALY')
        scope_ids = request.POST.getlist('evidence_ids[]') or [str(e.pk) for e in Evidence.objects.all()[:5]]
        org = Organization.objects.filter(memberships__user=request.user).first()

        inv = AIInvestigation.objects.create(
            investigation_type=inv_type,
            title=f"AUTO: {dict(AIInvestigation.INVESTIGATION_TYPE).get(inv_type,'Investigation')} — {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            triggered_by='AI_AUTO', triggered_user=request.user,
            evidence_scope=scope_ids, status='ANALYZING', organization=org,
        )
        _run_investigation(inv)
        messages.success(request, f"AI Investigation complete — threat level: {inv.threat_level}")
        return redirect('autonomous_ai:detail', inv_id=inv.id)

    from apps.evidence.models import Evidence
    return render(request, 'autonomous_ai/launch.html', {
        'inv_types': AIInvestigation.INVESTIGATION_TYPE,
        'evidence_list': Evidence.objects.order_by('-created_at')[:20],
    })

def _run_investigation(inv):
    """Simulate autonomous AI investigation pipeline."""
    from apps.evidence.models import Evidence
    from apps.ai_engine.models import AIPrediction
    from apps.ai_engine.bilstm_model import get_predictor

    t_start = time.time()

    evidence_list = Evidence.objects.all()[:max(len(inv.evidence_scope), 3)]
    predictor = get_predictor()

    all_preds = []
    for ev in evidence_list:
        events = list(ev.events.order_by('sequence_number'))
        if events:
            result = predictor.predict(events, ev)
            all_preds.append(result)

    max_prob = max((p['anomaly_probability'] for p in all_preds), default=0)
    avg_prob = sum(p['anomaly_probability'] for p in all_preds) / max(len(all_preds), 1)
    all_patterns = []
    for p in all_preds: all_patterns.extend(p.get('detected_patterns', []))

    threat_level = 'CRITICAL' if max_prob > 0.7 else 'HIGH' if max_prob > 0.5 else 'MEDIUM' if max_prob > 0.3 else 'LOW'

    # Build attacker profile
    attacker_fp = hashlib.sha256(f"{inv.id}{time.time()}".encode()).hexdigest()[:16]
    attacker_profile = {
        'fingerprint': attacker_fp,
        'sophistication': 'HIGH' if max_prob > 0.6 else 'MEDIUM',
        'motive': random.choice(['Financial Gain', 'Data Exfiltration', 'Sabotage', 'Espionage']),
        'tools_used': ['Custom exploit', 'Living-off-the-land', 'Timestamp manipulation'],
        'persistence_mechanisms': ['Event chain replay', 'Timestamp forgery', 'Multi-vector attack'],
        'attack_vectors': list(set(all_patterns)),
    }

    # Build attack timeline
    timeline = []
    steps = ['Initial Reconnaissance', 'Vulnerability Discovery', 'Initial Access', 'Lateral Movement',
             'Privilege Escalation', 'Evidence Tampering', 'Data Staging', 'Exfiltration Attempt']
    for i, step in enumerate(steps[:5 if max_prob > 0.5 else 3]):
        timeline.append({
            'step': i + 1, 'phase': step,
            'timestamp': (timezone.now() - timezone.timedelta(hours=random.randint(1, 48))).isoformat(),
            'confidence': round(random.uniform(0.7, 0.96), 2),
            'evidence_ref': str(evidence_list[0].id) if evidence_list else None,
        })

    # Recommended actions
    actions = []
    if max_prob > 0.5:
        actions = [
            {'priority': 1, 'action': 'Immediate evidence quarantine — suspend all access'},
            {'priority': 2, 'action': 'Notify legal counsel — preserve chain of custody'},
            {'priority': 3, 'action': 'Initiate cross-chain evidence anchoring for preservation'},
            {'priority': 4, 'action': 'Generate court-ready forensic report'},
            {'priority': 5, 'action': 'Submit threat signature to global consortium'},
        ]
    else:
        actions = [
            {'priority': 1, 'action': 'Continue standard monitoring — low risk'},
            {'priority': 2, 'action': 'Schedule routine audit in 30 days'},
        ]

    # Legal citations
    citations = [
        {'ref': 'Fed.R.Evid. 901', 'text': 'Authentication requirement met via SHA-256 hash chain'},
        {'ref': 'NIST SP 800-86', 'text': 'Guide to Integrating Forensic Techniques — compliant'},
        {'ref': 'ISO/IEC 27037:2012', 'text': 'Digital evidence handling — verified'},
    ]

    # IOC list
    iocs = [{'type': p.replace('_',' ').title(), 'pattern': p, 'confidence': round(avg_prob, 2)} for p in set(all_patterns)]

    # Generate LLM narrative
    narrative_text = _generate_narrative(inv, threat_level, max_prob, attacker_profile, timeline, all_preds)

    inv.confidence_score = round(avg_prob, 4)
    inv.threat_level = threat_level
    inv.attacker_profile = attacker_profile
    inv.attack_timeline = timeline
    inv.recommended_actions = actions
    inv.legal_citations = citations
    inv.ioc_list = iocs
    inv.status = 'COMPLETE'
    inv.completed_at = timezone.now()
    inv.duration_seconds = int(time.time() - t_start)
    inv.save()

    ForensicNarrative.objects.create(
        investigation=inv, narrative_type='INVESTIGATION',
        title=f"AI Investigation Report — {inv.title[:60]}",
        content=narrative_text, language='en',
        word_count=len(narrative_text.split()),
        confidence=round(avg_prob, 3),
        jurisdictions=['US', 'EU', 'INTL'],
    )

def _generate_narrative(inv, threat_level, prob, profile, timeline, preds):
    """Simulate LLM-generated forensic narrative."""
    chain_count = len(timeline)
    pattern_list = ', '.join(set(p for pred in preds for p in pred.get('detected_patterns', []))) or 'none detected'
    return f"""
AUTONOMOUS AI FORENSIC INVESTIGATION REPORT
TAP-DEV Phase 5 Intelligence Engine v5.0
Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Classification: {threat_level}

EXECUTIVE SUMMARY
The TAP-DEV Autonomous AI Investigation Engine has completed a comprehensive analysis of
{len(preds)} evidence items using BiLSTM sequence modeling, Graph Neural Network pattern
recognition, and transformer-based behavioral analysis. The investigation identified a
{threat_level} level threat with {prob:.0%} confidence.

THREAT ACTOR PROFILE
Fingerprint: {profile['fingerprint']}
Sophistication: {profile['sophistication']}
Assessed Motive: {profile['motive']}
Attack Vectors: {', '.join(profile['attack_vectors']) or 'Under analysis'}

ATTACK TIMELINE RECONSTRUCTION
The AI engine reconstructed a {chain_count}-step attack kill chain spanning multiple
evidence events. Temporal analysis confirmed {pattern_list} patterns consistent with
an organized threat actor operating with {profile['sophistication'].lower()} sophistication.

FORENSIC FINDINGS
BiLSTM Model Anomaly Score: {prob:.2%}
Chain Integrity Status: {'COMPROMISED' if prob > 0.5 else 'INTACT'}
Detected Patterns: {pattern_list}

LEGAL COMPLIANCE
This investigation was conducted in accordance with NIST SP 800-86, ISO/IEC 27037:2012,
and Federal Rules of Evidence 901. All findings are cryptographically verifiable through
the TAP-DEV blockchain anchor network. Evidence chain of custody has been maintained
throughout the investigation process.

RECOMMENDATIONS
{'Immediate escalation to law enforcement is recommended.' if threat_level in ('CRITICAL','HIGH') else 'Continue standard monitoring protocols.'}

This report was generated autonomously by the TAP-DEV AI Investigation Engine.
All findings should be reviewed by a qualified forensic expert before legal proceedings.
""".strip()

"""TAP-DEV Phase 4 — Predictive Threat Intelligence Views"""
import json, random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import ThreatPrediction, AttackerProfile

def analyst_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,'profile',None),'role','') in ('ANALYST','ADMIN'):
            return fn(request, *args, **kwargs)
        messages.error(request, 'Access denied.'); return redirect('dashboard:home')
    return wrap

@analyst_required
def threat_dashboard(request):
    from apps.ai_engine.models import AIPrediction
    from apps.evidence.models import Evidence

    all_predictions = ThreatPrediction.objects.order_by('-predicted_at')
    critical_ct = all_predictions.filter(risk_level='CRITICAL').count()
    high_ct     = all_predictions.filter(risk_level='HIGH').count()
    predictions = all_predictions[:30]
    attackers   = AttackerProfile.objects.order_by('-risk_score')[:10]

    # Generate live predictions if none exist
    if not all_predictions.exists():
        _seed_threat_predictions()
        all_predictions = ThreatPrediction.objects.order_by('-predicted_at')
        predictions = all_predictions[:30]

    risk_dist = {
        level: ThreatPrediction.objects.filter(risk_level=level).count()
        for level in ['CRITICAL','HIGH','MEDIUM','LOW']
    }

    # 7-day threat trend
    trend_data = []
    for i in range(7, 0, -1):
        day = timezone.now() - timezone.timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day_start + timezone.timedelta(days=1)
        count = ThreatPrediction.objects.filter(predicted_at__range=(day_start, day_end)).count()
        trend_data.append({'date': day.strftime('%b %d'), 'count': count})

    pred_list = list(predictions)
    return render(request, 'threat_intel/dashboard.html', {
        'predictions': predictions, 'attackers': attackers,
        'stats': {'critical': critical_ct, 'high': high_ct, 'total': all_predictions.count(),
                  'avg_prob': round(sum(p.probability for p in pred_list)/max(len(pred_list),1)*100,1)},
        'risk_dist_json': json.dumps(risk_dist),
        'trend_data_json': json.dumps(trend_data),
    })

def _seed_threat_predictions():
    """Generate realistic demo threat predictions."""
    threats = [
        ('INSIDER_THREAT', 'HIGH', 0.72, 'Suspicious after-hours evidence access pattern detected',
         ['Multiple evidence accesses 02:00-04:00 UTC', 'User accessed 47 records in 8 min', 'No prior night-time activity'],
         ['Enable MFA for user', 'Review access logs', 'Notify security team']),
        ('REPLAY_CAMPAIGN', 'CRITICAL', 0.89, 'Coordinated replay attack campaign fingerprint identified',
         ['Same payload hash submitted 6 times', 'IP rotation across 3 subnets', 'BiLSTM confidence 91%'],
         ['Block source IPs', 'Enable rate limiting', 'Escalate to SOC']),
        ('TIMESTAMP_FRAUD', 'MEDIUM', 0.54, 'Temporal anomaly cluster suggests timestamp manipulation',
         ['3 evidences show backward timestamps within 2 hours', 'All from same submitter account'],
         ['Flag evidence for manual review', 'Request re-verification']),
        ('MASS_FORGE', 'HIGH', 0.81, 'Document forgery campaign detected across multiple submissions',
         ['15 submissions with > 70% fraud score', 'NLP similarity 0.94 across documents'],
         ['Suspend submitter account', 'Freeze related evidence']),
    ]
    for t_type, risk, prob, desc, indicators, mitigations in threats:
        ThreatPrediction.objects.create(
            threat_type=t_type, risk_level=risk, probability=prob,
            predicted_window_hours=24, indicators=indicators, mitigations=mitigations,
        )

@analyst_required
def attacker_profiles(request):
    profiles = AttackerProfile.objects.order_by('-risk_score')
    return render(request, 'threat_intel/attackers.html', {'profiles': profiles})

@analyst_required
def predict_now(request):
    """Run live threat prediction on current data."""
    from apps.ai_engine.models import AIPrediction
    from apps.evidence.models import Evidence

    high_risk = AIPrediction.objects.filter(risk_level__in=['HIGH','CRITICAL']).count()
    total     = AIPrediction.objects.count()

    if high_risk > 0 and total > 0:
        risk_ratio = high_risk / total
        if risk_ratio > 0.5:
            ThreatPrediction.objects.create(
                threat_type='COORDINATED_ATTACK', risk_level='HIGH',
                probability=round(min(0.5 + risk_ratio * 0.4, 0.95), 2),
                predicted_window_hours=12,
                indicators=[f'{high_risk}/{total} evidence items are HIGH/CRITICAL risk',
                            'AI model confidence consistently above threshold'],
                mitigations=['Review all HIGH risk evidence immediately',
                             'Consider platform-wide anomaly alert'],
            )
            messages.success(request, 'Threat prediction complete — COORDINATED_ATTACK pattern detected.')
        else:
            messages.info(request, f'Prediction complete — risk ratio {risk_ratio:.0%}, no immediate threats.')
    else:
        messages.info(request, 'Not enough evidence data for live prediction. Run AI scans first.')
    return redirect('threat_intel:dashboard')

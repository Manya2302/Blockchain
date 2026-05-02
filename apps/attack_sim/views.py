"""TAP-DEV Phase 3 — Attack Simulation Views"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import AttackSimulation
from .simulator import AttackSimulator


def require_admin(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
        if role != 'ADMIN':
            messages.error(request, 'Admin access required for attack simulation.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_admin
def sim_dashboard(request):
    """Attack simulation dashboard."""
    sims = AttackSimulation.objects.select_related('target_evidence', 'initiated_by').order_by('-initiated_at')
    from apps.evidence.models import Evidence
    evidence_list = Evidence.objects.filter(is_latest_version=True).order_by('-created_at')[:30]

    attack_types = AttackSimulation.ATTACK_TYPES
    detected_count = sims.filter(ai_detected=True).count()
    evaded_count   = sims.filter(ai_detected=False).count()
    total          = sims.count()

    return render(request, 'attack_sim/dashboard.html', {
        'sims': sims[:20],
        'evidence_list': evidence_list,
        'attack_types': attack_types,
        'stats': {
            'total': total,
            'detected': detected_count,
            'evaded': evaded_count,
            'detection_rate': round(detected_count / max(total, 1) * 100, 1),
        }
    })


@require_admin
def run_simulation(request):
    """Launch a new attack simulation."""
    if request.method != 'POST':
        return redirect('attack_sim:dashboard')

    evidence_id = request.POST.get('evidence_id')
    attack_type = request.POST.get('attack_type')

    from apps.evidence.models import Evidence
    evidence = get_object_or_404(Evidence, id=evidence_id)

    sim = AttackSimulation.objects.create(
        attack_type=attack_type,
        target_evidence=evidence,
        initiated_by=request.user,
        status='RUNNING',
        description=request.POST.get('description', ''),
    )

    try:
        simulator = AttackSimulator(sim, evidence, request.user)
        logs, injected_ids = simulator.run()

        sim.events_injected = len(injected_ids)
        sim.artifacts = injected_ids
        sim.log_output = '\n'.join(logs)
        sim.status = 'RUNNING'
        sim.save()

        # Run AI detection
        from apps.events.models import Event
        from apps.ai_engine.bilstm_model import get_predictor
        from apps.ai_engine.models import AIPrediction, AIModelVersion

        events = list(Event.objects.filter(evidence=evidence).order_by('sequence_number'))
        predictor = get_predictor()
        result = predictor.predict(events, evidence)

        active_model = AIModelVersion.objects.filter(is_active=True).first()
        pred = AIPrediction.objects.create(
            evidence=evidence,
            model_version=active_model,
            anomaly_probability=result['anomaly_probability'] * 100,
            risk_level=result['risk_level'],
            confidence=result['confidence'],
            feature_vector=result['feature_vector'],
            explanation=result['explanation'],
            detected_patterns=result['detected_patterns'],
            hybrid_score=result['anomaly_probability'] * 100,
        )

        sim.ai_prediction = pred
        sim.ai_confidence = result['confidence'] * 100
        sim.ai_detected = result['risk_level'] in ('HIGH', 'CRITICAL') or result['anomaly_probability'] > 0.45
        sim.status = 'DETECTED' if sim.ai_detected else 'EVADED'
        sim.save()

        if sim.ai_detected:
            messages.success(request, f"Simulation complete — AI DETECTED the {sim.get_attack_type_display()} attack! (confidence: {result['confidence']:.0%})")
        else:
            messages.warning(request, f"Simulation complete — AI DID NOT detect the attack. (probability: {result['anomaly_probability']:.0%})")

    except Exception as e:
        sim.status = 'ERROR'
        sim.log_output = str(e)
        sim.save()
        messages.error(request, f"Simulation error: {e}")

    return redirect('attack_sim:detail', sim_id=sim.id)


@require_admin
def sim_detail(request, sim_id):
    """Detailed simulation result view."""
    sim = get_object_or_404(AttackSimulation, id=sim_id)
    from apps.events.models import Event
    injected_events = Event.objects.filter(id__in=sim.artifacts)

    return render(request, 'attack_sim/detail.html', {
        'sim': sim,
        'injected_events': injected_events,
        'log_lines': sim.log_output.split('\n') if sim.log_output else [],
    })

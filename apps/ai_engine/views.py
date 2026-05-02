"""TAP-DEV Phase 3 — AI Engine Views"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AIModelVersion, AIPrediction, TrainingRun
from .bilstm_model import get_predictor, extract_features, FEATURE_NAMES
from apps.users.security import parse_json_body

logger = logging.getLogger(__name__)


def require_analyst(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
        if role not in ('ANALYST', 'ADMIN'):
            messages.error(request, 'Analyst or Admin access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_admin(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
        if role != 'ADMIN':
            messages.error(request, 'Admin access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_analyst
def ai_dashboard(request):
    """AI engine overview dashboard."""
    predictions = AIPrediction.objects.select_related('evidence', 'model_version').order_by('-predicted_at')[:20]
    active_model = AIModelVersion.objects.filter(is_active=True).first()
    all_models   = AIModelVersion.objects.order_by('-trained_at')[:5]
    training_runs = TrainingRun.objects.order_by('-started_at')[:5]

    # Stats
    total_predictions = AIPrediction.objects.count()
    critical_count    = AIPrediction.objects.filter(risk_level__in=['HIGH', 'CRITICAL']).count()
    safe_count        = AIPrediction.objects.filter(risk_level='SAFE').count()

    # Risk distribution for chart
    from django.db.models import Count
    risk_dist = (
        AIPrediction.objects.values('risk_level')
        .annotate(c=Count('risk_level'))
        .order_by('risk_level')
    )
    risk_chart = {r['risk_level']: r['c'] for r in risk_dist}

    # Recent trend (last 14 predictions anomaly prob)
    recent_probs = list(
        AIPrediction.objects.order_by('-predicted_at')[:14]
        .values_list('anomaly_probability', flat=True)
    )[::-1]

    predictor = get_predictor()
    feature_importances = predictor.get_feature_importances()
    top_features = sorted(feature_importances.items(), key=lambda x: -x[1])[:10]

    return render(request, 'ai_engine/dashboard.html', {
        'predictions': predictions,
        'active_model': active_model,
        'all_models': all_models,
        'training_runs': training_runs,
        'stats': {
            'total': total_predictions,
            'critical': critical_count,
            'safe': safe_count,
            'detection_rate': round(critical_count / max(total_predictions, 1) * 100, 1),
        },
        'risk_chart_json': json.dumps(risk_chart),
        'recent_probs_json': json.dumps(recent_probs),
        'top_features': top_features,
        'feature_names': FEATURE_NAMES,
    })


@require_analyst
def prediction_detail(request, prediction_id):
    """Detailed prediction view with explanation."""
    pred = get_object_or_404(AIPrediction, id=prediction_id)
    events = list(pred.evidence.events.order_by('sequence_number'))

    # Feature importances for this prediction
    predictor = get_predictor()
    fi = predictor.get_feature_importances()
    fv = pred.feature_vector

    feature_detail = []
    for name in FEATURE_NAMES:
        feature_detail.append({
            'name': name,
            'value': round(fv.get(name, 0), 4),
            'importance': round(fi.get(name, 0), 4),
        })
    feature_detail.sort(key=lambda x: -x['importance'])

    return render(request, 'ai_engine/prediction_detail.html', {
        'pred': pred,
        'events': events,
        'feature_detail': feature_detail[:12],
        'explanation': pred.explanation,
        'patterns': pred.detected_patterns,
    })


@require_analyst
def model_comparison(request):
    """CNN+BiLSTM vs BiLSTM model comparison dashboard."""
    models = AIModelVersion.objects.order_by('-trained_at')[:8]

    # Generate comparison metrics if we have models
    model_data = []
    for m in models:
        cm = m.confusion_matrix
        model_data.append({
            'id': m.id,
            'type': m.get_model_type_display(),
            'version': m.version_tag,
            'accuracy': round(m.accuracy * 100, 1),
            'precision': round(m.precision * 100, 1),
            'recall': round(m.recall * 100, 1),
            'f1': round(m.f1_score * 100, 1),
            'auc': round(m.auc_roc * 100, 1),
            'samples': m.training_samples,
            'is_active': m.is_active,
            'confusion_matrix': cm,
        })

    # If no real model records, show demo comparison data
    if not model_data:
        model_data = _demo_model_comparison()

    return render(request, 'ai_engine/model_comparison.html', {
        'model_data': model_data,
        'model_data_json': json.dumps(model_data),
    })


def _demo_model_comparison():
    return [
        {
            'id': 1, 'type': 'BiLSTM Sequence Model', 'version': 'v1.0',
            'accuracy': 94.2, 'precision': 92.8, 'recall': 95.1, 'f1': 93.9, 'auc': 97.3,
            'samples': 1240, 'is_active': True,
            'confusion_matrix': {'tn': 580, 'fp': 22, 'fn': 18, 'tp': 320}
        },
        {
            'id': 2, 'type': 'CNN+BiLSTM Ensemble', 'version': 'v0.9',
            'accuracy': 96.8, 'precision': 95.4, 'recall': 97.2, 'f1': 96.3, 'auc': 98.7,
            'samples': 1240, 'is_active': False,
            'confusion_matrix': {'tn': 591, 'fp': 11, 'fn': 10, 'tp': 328}
        },
        {
            'id': 3, 'type': 'Random Forest Hybrid', 'version': 'v1.1',
            'accuracy': 91.5, 'precision': 89.3, 'recall': 90.7, 'f1': 90.0, 'auc': 94.8,
            'samples': 1240, 'is_active': False,
            'confusion_matrix': {'tn': 562, 'fp': 40, 'fn': 35, 'tp': 303}
        },
    ]


@require_admin
def trigger_training(request):
    """Trigger model retraining on current evidence data."""
    if request.method != 'POST':
        return redirect('ai:dashboard')

    from apps.evidence.models import Evidence

    run = TrainingRun.objects.create(triggered_by=request.user)

    try:
        predictor = get_predictor()
        evidence_qs = Evidence.objects.all()
        metrics, duration = predictor.retrain(evidence_qs, triggered_by=request.user)

        # Save model version record
        import time
        model_version = AIModelVersion.objects.create(
            model_type='RF_HYBRID',
            version_tag=f"v{int(time.time())}",
            status='ACTIVE',
            trained_by=request.user,
            training_samples=metrics['samples'],
            accuracy=metrics['accuracy'],
            precision=metrics['precision'],
            recall=metrics['recall'],
            f1_score=metrics['f1_score'],
            auc_roc=metrics.get('auc_roc', 0.0),
            confusion_matrix=metrics.get('confusion_matrix', {}),
            feature_importances=predictor.get_feature_importances(),
            is_active=True,
        )

        # Deactivate old models
        AIModelVersion.objects.exclude(id=model_version.id).update(is_active=False)

        run.status = 'COMPLETE'
        run.completed_at = timezone.now()
        run.duration_seconds = duration
        run.samples_used = metrics['samples']
        run.model_produced = model_version
        run.log_output = json.dumps(metrics, indent=2)
        run.save()

        messages.success(request, f"Model retrained successfully. F1: {metrics['f1_score']:.2%}, Accuracy: {metrics['accuracy']:.2%}")

    except Exception as e:
        run.status = 'FAILED'
        run.log_output = str(e)
        run.completed_at = timezone.now()
        run.save()
        logger.exception("Training failed")
        messages.error(request, f"Training failed: {e}")

    return redirect('ai:dashboard')


@require_analyst
def run_prediction(request, pk):
    """Run AI prediction for a specific evidence item."""
    from apps.evidence.models import Evidence
    from apps.events.models import Event
    from apps.analysis.detector import AnomalyDetector

    evidence = get_object_or_404(Evidence, pk=pk)
    events = list(Event.objects.filter(evidence=evidence).order_by('sequence_number'))

    predictor = get_predictor()
    result = predictor.predict(events, evidence)

    # Get rule-based severity for hybrid
    detector = AnomalyDetector(evidence)
    detector.run()
    from apps.analysis.models import Anomaly
    high_anomalies = Anomaly.objects.filter(evidence=evidence, severity='HIGH', is_resolved=False)
    rule_severity = 'HIGH' if high_anomalies.exists() else 'MEDIUM' if Anomaly.objects.filter(
        evidence=evidence, severity='MEDIUM', is_resolved=False).exists() else 'LOW'

    # Hybrid score
    rule_boost = {'HIGH': 0.2, 'MEDIUM': 0.1, 'LOW': 0.02}.get(rule_severity, 0)
    hybrid = min(result['anomaly_probability'] + rule_boost, 1.0)

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
        rule_based_severity=rule_severity,
        hybrid_score=hybrid * 100,
    )

    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'prediction_id': pred.id,
            'anomaly_probability': pred.anomaly_probability,
            'risk_level': pred.risk_level,
            'confidence': pred.confidence,
            'hybrid_score': pred.hybrid_score,
            'detected_patterns': pred.detected_patterns,
        })

    messages.success(request, f"AI analysis complete: Risk level {pred.risk_level} ({pred.anomaly_probability:.1f}% probability)")
    return redirect('evidence:detail', pk=pk)


@require_analyst
def api_predict(request):
    """REST endpoint for external AI predictions."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = parse_json_body(request, max_bytes=8 * 1024)
        evidence_id = int(data.get('evidence_id'))
        from apps.evidence.models import Evidence
        from apps.events.models import Event

        evidence = Evidence.objects.get(id=evidence_id)
        events = list(Event.objects.filter(evidence=evidence).order_by('sequence_number'))
        predictor = get_predictor()
        result = predictor.predict(events, evidence)
        return JsonResponse(result)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid prediction request'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Prediction failed'}, status=400)

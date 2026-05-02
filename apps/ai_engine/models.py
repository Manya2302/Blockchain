"""
TAP-DEV Phase 3 — AI Engine Models

Stores BiLSTM anomaly predictions, model metrics, and training run records.
The hybrid engine combines:
  1. Rule-based detector (Phase 1 fallback)
  2. BiLSTM sequence model (primary)
  3. CNN+BiLSTM ensemble (experimental comparison)
"""
from django.db import models
from django.contrib.auth.models import User


class AIModelVersion(models.Model):
    """Tracks trained model versions and their metrics."""
    MODEL_TYPE_CHOICES = [
        ('BILSTM',     'BiLSTM Sequence Model'),
        ('CNN_BILSTM', 'CNN+BiLSTM Ensemble'),
        ('RF_HYBRID',  'Random Forest Hybrid'),
        ('ISOLATION',  'Isolation Forest'),
    ]
    STATUS_CHOICES = [
        ('TRAINING', 'Training'),
        ('ACTIVE',   'Active'),
        ('RETIRED',  'Retired'),
        ('FAILED',   'Failed'),
    ]

    model_type      = models.CharField(max_length=20, choices=MODEL_TYPE_CHOICES)
    version_tag     = models.CharField(max_length=50)
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='TRAINING')
    trained_at      = models.DateTimeField(auto_now_add=True)
    trained_by      = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    training_samples = models.IntegerField(default=0)
    # Metrics
    accuracy        = models.FloatField(default=0.0)
    precision       = models.FloatField(default=0.0)
    recall          = models.FloatField(default=0.0)
    f1_score        = models.FloatField(default=0.0)
    auc_roc         = models.FloatField(default=0.0)
    # Confusion matrix: stored as JSON
    confusion_matrix = models.JSONField(default=dict)
    # Feature importances
    feature_importances = models.JSONField(default=dict)
    # Model file path
    model_path      = models.CharField(max_length=500, blank=True)
    notes           = models.TextField(blank=True)
    is_active       = models.BooleanField(default=False)

    class Meta:
        db_table = 'tap_ai_models'
        ordering = ['-trained_at']

    def __str__(self):
        return f"{self.get_model_type_display()} v{self.version_tag} [{self.status}]"

    @property
    def f1_display(self):
        return f"{self.f1_score * 100:.1f}%"

    @property
    def accuracy_display(self):
        return f"{self.accuracy * 100:.1f}%"


class AIPrediction(models.Model):
    """Stores AI anomaly prediction results for each evidence item."""
    RISK_LEVEL_CHOICES = [
        ('SAFE',     'Safe'),
        ('LOW',      'Low Risk'),
        ('MEDIUM',   'Medium Risk'),
        ('HIGH',     'High Risk'),
        ('CRITICAL', 'Critical'),
    ]

    evidence        = models.ForeignKey(
        'tap_evidence.Evidence', on_delete=models.CASCADE, related_name='ai_predictions'
    )
    model_version   = models.ForeignKey(
        AIModelVersion, null=True, blank=True, on_delete=models.SET_NULL
    )
    predicted_at    = models.DateTimeField(auto_now_add=True)
    # Core prediction
    anomaly_probability = models.FloatField(default=0.0)   # 0.0 – 1.0
    risk_level      = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='SAFE')
    confidence      = models.FloatField(default=0.0)        # model confidence
    # Feature vector snapshot
    feature_vector  = models.JSONField(default=dict)
    # Explanation
    explanation     = models.JSONField(default=list)        # list of explanation strings
    # Attack types detected
    detected_patterns = models.JSONField(default=list)      # replay_attack, timestamp_forge, etc.
    # Rule-based fallback result
    rule_based_severity = models.CharField(max_length=10, blank=True)
    # Combined hybrid score
    hybrid_score    = models.FloatField(default=0.0)

    class Meta:
        db_table = 'tap_ai_predictions'
        ordering = ['-predicted_at']

    def __str__(self):
        return f"Prediction for Evidence#{self.evidence_id}: {self.risk_level} ({self.anomaly_probability:.1f}%)"

    @property
    def risk_color(self):
        return {
            'SAFE': '#10b981', 'LOW': '#84cc16', 'MEDIUM': '#f59e0b',
            'HIGH': '#ef4444', 'CRITICAL': '#dc2626'
        }.get(self.risk_level, '#6b7280')

    @property
    def risk_icon(self):
        return {
            'SAFE': '✓', 'LOW': '◎', 'MEDIUM': '▲',
            'HIGH': '⬟', 'CRITICAL': '⬣'
        }.get(self.risk_level, '●')


class TrainingRun(models.Model):
    """Records each training pipeline execution."""
    STATUS_CHOICES = [('RUNNING', 'Running'), ('COMPLETE', 'Complete'), ('FAILED', 'Failed')]

    started_at      = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='RUNNING')
    triggered_by    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    samples_used    = models.IntegerField(default=0)
    epochs          = models.IntegerField(default=0)
    log_output      = models.TextField(blank=True)
    model_produced  = models.ForeignKey(AIModelVersion, null=True, blank=True, on_delete=models.SET_NULL)
    duration_seconds = models.IntegerField(default=0)

    class Meta:
        db_table = 'tap_ai_training_runs'
        ordering = ['-started_at']

    def __str__(self):
        return f"Training Run #{self.id} [{self.status}]"

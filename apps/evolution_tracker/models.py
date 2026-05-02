"""
TAP-DEV Phase 3+ — Document Evolution Tracker Models
Tracks gradual document mutations across versions to detect fraud.
Enhanced with AI-powered evolution analysis.
"""
from django.db import models
from django.contrib.auth.models import User


class DocumentVersion(models.Model):
    """Snapshot of a document version for comparison."""
    CHANGE_TYPE = [
        ('MINOR',    'Minor Edit'),
        ('MAJOR',    'Major Revision'),
        ('FORGED',   'Suspected Forgery'),
        ('CRITICAL', 'Critical Alteration'),
    ]

    evidence          = models.ForeignKey(
        'tap_evidence.Evidence', on_delete=models.CASCADE, related_name='doc_versions'
    )
    version_number    = models.IntegerField(default=1)
    compared_to       = models.ForeignKey(
        'tap_evidence.Evidence', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='comparison_target'
    )
    analyzed_at       = models.DateTimeField(auto_now_add=True)

    # Text diff metrics
    text_similarity   = models.FloatField(default=1.0)   # 0.0–1.0
    words_added       = models.IntegerField(default=0)
    words_removed     = models.IntegerField(default=0)
    chars_changed     = models.IntegerField(default=0)

    # Structural changes
    file_size_delta   = models.BigIntegerField(default=0)  # bytes
    hash_changed      = models.BooleanField(default=False)

    # Fraud signals
    change_type       = models.CharField(max_length=20, choices=CHANGE_TYPE, default='MINOR')
    fraud_score       = models.FloatField(default=0.0)     # 0.0–1.0
    fraud_signals     = models.JSONField(default=list)     # list of signal dicts
    diff_summary      = models.TextField(blank=True)

    class Meta:
        db_table = 'tap_doc_versions'
        ordering = ['-analyzed_at']

    def __str__(self):
        return f"DocVersion #{self.evidence_id} v{self.version_number} [{self.change_type}]"

    @property
    def fraud_percent(self):
        return round(self.fraud_score * 100, 1)


class EvolutionAIAnalysis(models.Model):
    """
    AI-powered analysis of a complete document version evolution chain.
    Stores sequence-based anomaly detection results.
    """
    RISK_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Moderate Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]

    evidence          = models.ForeignKey(
        'tap_evidence.Evidence', on_delete=models.CASCADE, related_name='evolution_analyses'
    )
    analyzed_by       = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    analyzed_at       = models.DateTimeField(auto_now_add=True)

    # AI Score
    anomaly_score     = models.FloatField(default=0.0)     # 0.0–1.0
    risk_level        = models.CharField(max_length=10, choices=RISK_CHOICES, default='LOW')

    # Feature vector (individual scores)
    features          = models.JSONField(default=dict)
    # Detected tampering patterns
    patterns          = models.JSONField(default=list)

    # Chain metadata
    version_count     = models.IntegerField(default=0)
    comparison_count  = models.IntegerField(default=0)
    chain_span_days   = models.IntegerField(default=0)

    # Summary
    summary           = models.TextField(blank=True)

    class Meta:
        db_table = 'tap_evolution_ai'
        ordering = ['-analyzed_at']

    def __str__(self):
        return f"EvolutionAI #{self.evidence_id} [{self.risk_level}] {self.anomaly_percent}%"

    @property
    def anomaly_percent(self):
        return round(self.anomaly_score * 100, 1)

    @property
    def risk_color(self):
        return {
            'LOW': '#10b981',
            'MEDIUM': '#f59e0b',
            'HIGH': '#ef4444',
            'CRITICAL': '#dc2626',
        }.get(self.risk_level, '#6b7280')

    @property
    def risk_icon(self):
        return {
            'LOW': '✓',
            'MEDIUM': '⚠',
            'HIGH': '⚠',
            'CRITICAL': '🚨',
        }.get(self.risk_level, '◈')

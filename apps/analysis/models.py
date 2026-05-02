"""
TAP-DEV Analysis App — Anomaly Model
Stores detected anomalies for each evidence chain.
Phase 1: Rule-based detection
Phase 3 (future): BiLSTM sequence anomaly detection
"""
from django.db import models


class Anomaly(models.Model):
    SEVERITY_CHOICES = [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')]

    ANOMALY_TYPES = [
        ('INVALID_SEQUENCE',   'Invalid Event Sequence'),
        ('BACKWARD_TIMESTAMP', 'Backward Timestamp'),
        ('MISSING_STEP',       'Missing Logical Step'),
        ('LARGE_GAP',          'Large Time Gap'),
        ('DUPLICATE_EVENT',    'Duplicate Event Type'),
        ('HASH_MISMATCH',      'Chain Hash Mismatch'),
        ('PREMATURE_VERIFY',   'Premature Verification'),
        ('ORPHAN_MODIFY',      'Orphan Modification'),
    ]

    evidence     = models.ForeignKey('tap_evidence.Evidence', on_delete=models.CASCADE, related_name='anomalies')
    anomaly_type = models.CharField(max_length=50, choices=ANOMALY_TYPES)
    description  = models.TextField()
    severity     = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    detected_at  = models.DateTimeField(auto_now_add=True)
    related_event = models.ForeignKey('tap_events.Event', null=True, blank=True, on_delete=models.SET_NULL)
    is_resolved  = models.BooleanField(default=False)
    resolved_by  = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    resolved_at  = models.DateTimeField(null=True, blank=True)
    notes        = models.TextField(blank=True)

    class Meta:
        db_table = 'tap_anomalies'
        ordering = ['-detected_at']

    def __str__(self):
        return f"[{self.severity}] {self.anomaly_type} on Evidence#{self.evidence_id}"

    def get_severity_class(self):
        return {'LOW': 'severity-low', 'MEDIUM': 'severity-medium', 'HIGH': 'severity-high'}.get(self.severity, '')

    def get_severity_icon(self):
        return {'LOW': '◉', 'MEDIUM': '▲', 'HIGH': '⬟'}.get(self.severity, '●')

"""
TAP-DEV Phase 3 — Temporal Attack Simulation Module
Admins simulate known attack vectors to validate AI detection capability.
"""
from django.db import models
from django.contrib.auth.models import User


class AttackSimulation(models.Model):
    ATTACK_TYPES = [
        ('TIMESTAMP_TAMPER',    'Timestamp Tampering'),
        ('LOG_DELETION',        'Log Deletion Attack'),
        ('REPLAY_ATTACK',       'Event Replay Attack'),
        ('FORGED_UPLOAD',       'Forged Upload Injection'),
        ('DUPLICATE_EVENTS',    'Duplicate Event Injection'),
        ('DELAYED_VERIFY',      'Delayed Verification'),
        ('HASH_COLLISION',      'Hash Collision Attempt'),
        ('PRIVILEGE_ESCALATION','Privilege Escalation'),
        ('CHAIN_TRUNCATION',    'Chain Truncation'),
        ('METADATA_FORGE',      'Metadata Forgery'),
    ]
    STATUS_CHOICES = [
        ('PENDING',   'Pending'),
        ('RUNNING',   'Running'),
        ('DETECTED',  'Detected by AI'),
        ('EVADED',    'Evaded Detection'),
        ('ERROR',     'Error'),
    ]

    attack_type     = models.CharField(max_length=30, choices=ATTACK_TYPES)
    target_evidence = models.ForeignKey(
        'tap_evidence.Evidence', on_delete=models.CASCADE, related_name='simulations'
    )
    initiated_by    = models.ForeignKey(User, on_delete=models.CASCADE)
    initiated_at    = models.DateTimeField(auto_now_add=True)
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    description     = models.TextField(blank=True)
    parameters      = models.JSONField(default=dict)

    # AI Detection result
    ai_detected     = models.BooleanField(null=True)
    ai_confidence   = models.FloatField(null=True)
    ai_prediction   = models.ForeignKey(
        'tap_ai.AIPrediction', null=True, blank=True, on_delete=models.SET_NULL
    )

    # Simulation output
    events_injected = models.IntegerField(default=0)
    artifacts       = models.JSONField(default=list)  # list of created/modified artifact IDs
    log_output      = models.TextField(blank=True)

    class Meta:
        db_table = 'tap_attack_sims'
        ordering = ['-initiated_at']

    def __str__(self):
        return f"{self.get_attack_type_display()} on Evidence#{self.target_evidence_id} [{self.status}]"

    @property
    def detection_icon(self):
        if self.ai_detected is None: return '⏳'
        return '✓ Detected' if self.ai_detected else '✕ Evaded'

    @property
    def detection_color(self):
        if self.ai_detected is None: return '#6b7280'
        return '#10b981' if self.ai_detected else '#ef4444'

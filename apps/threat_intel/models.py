"""TAP-DEV Phase 4 — Predictive Threat Intelligence Models"""
from django.db import models
from django.contrib.auth.models import User


class ThreatPrediction(models.Model):
    THREAT_TYPE = [
        ('INSIDER_THREAT','Insider Threat'),('REPLAY_CAMPAIGN','Replay Attack Campaign'),
        ('TIMESTAMP_FRAUD','Timestamp Fraud Pattern'),('MASS_FORGE','Mass Document Forgery'),
        ('COORDINATED_ATTACK','Coordinated Multi-User Attack'),('AI_EVASION','AI Evasion Attempt'),
        ('DATA_EXFIL','Data Exfiltration Signal'),('PRIVILEGE_ABUSE','Privilege Abuse'),
    ]
    RISK_LEVEL = [('CRITICAL','Critical'),('HIGH','High'),('MEDIUM','Medium'),('LOW','Low')]

    organization  = models.ForeignKey('tap_org.Organization', null=True, blank=True, on_delete=models.SET_NULL)
    threat_type   = models.CharField(max_length=30, choices=THREAT_TYPE)
    risk_level    = models.CharField(max_length=10, choices=RISK_LEVEL)
    probability   = models.FloatField()  # 0.0-1.0
    predicted_at  = models.DateTimeField(auto_now_add=True)
    predicted_window_hours = models.IntegerField(default=24)
    target_user   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='threat_predictions')
    evidence_refs = models.JSONField(default=list)
    indicators    = models.JSONField(default=list)
    mitigations   = models.JSONField(default=list)
    is_confirmed  = models.BooleanField(null=True)
    model_version = models.CharField(max_length=50, default='threat-intel-v1')

    class Meta:
        db_table = 'tap_threat_predictions'
        ordering = ['-predicted_at']

    def __str__(self): return f"{self.threat_type} [{self.risk_level}] {self.probability:.0%}"

    @property
    def risk_color(self):
        return {'CRITICAL':'#dc2626','HIGH':'#ef4444','MEDIUM':'#f59e0b','LOW':'#84cc16'}.get(self.risk_level,'#6b7280')


class AttackerProfile(models.Model):
    """Built-up profile of a recurring attacker pattern."""
    fingerprint   = models.CharField(max_length=64, unique=True)
    first_seen    = models.DateTimeField(auto_now_add=True)
    last_seen     = models.DateTimeField(auto_now=True)
    incident_count = models.IntegerField(default=1)
    known_ips     = models.JSONField(default=list)
    known_patterns = models.JSONField(default=list)
    organization  = models.ForeignKey('tap_org.Organization', null=True, blank=True, on_delete=models.SET_NULL)
    risk_score    = models.FloatField(default=0.0)
    notes         = models.TextField(blank=True)

    class Meta:
        db_table = 'tap_attacker_profiles'

    def __str__(self): return f"Attacker {self.fingerprint[:12]}... (score:{self.risk_score:.2f})"

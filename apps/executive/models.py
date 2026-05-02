"""TAP-DEV Phase 4 — Executive Dashboard Models"""
from django.db import models


class ExecutiveKPI(models.Model):
    """Stores daily/weekly KPI snapshots for executive dashboards."""
    organization  = models.ForeignKey('tap_org.Organization', on_delete=models.CASCADE, related_name='kpis')
    date          = models.DateField(auto_now_add=True)
    evidence_count = models.IntegerField(default=0)
    ai_scans      = models.IntegerField(default=0)
    threats_detected = models.IntegerField(default=0)
    fraud_prevented_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    blockchain_anchors = models.IntegerField(default=0)
    compliance_score = models.FloatField(default=0.0)
    active_users  = models.IntegerField(default=0)
    api_calls     = models.IntegerField(default=0)
    iot_pushes    = models.IntegerField(default=0)
    avg_trust_score = models.FloatField(default=0.0)
    class Meta:
        db_table = 'tap_executive_kpis'
        unique_together = ('organization', 'date')
    def __str__(self): return f"{self.organization.name} KPI {self.date}"

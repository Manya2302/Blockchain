"""TAP-DEV Phase 5 — Self-Healing Blockchain Infrastructure"""
from django.db import models
from django.contrib.auth.models import User


class InfrastructureHealth(models.Model):
    """Real-time health status of all blockchain and storage nodes."""
    COMPONENT = [("BLOCKCHAIN_NODE","Blockchain Node"),("IPFS_NODE","IPFS Node"),
                 ("AI_CLUSTER","AI Inference Cluster"),("DATABASE","Database Node"),
                 ("API_GATEWAY","API Gateway"),("EVIDENCE_STORE","Evidence Store"),
                 ("FORENSIC_NODE","Forensic Network Node")]
    STATUS = [("HEALTHY","Healthy"),("DEGRADED","Degraded"),("CRITICAL","Critical"),
              ("HEALING","Self-Healing"),("OFFLINE","Offline"),("RECOVERED","Recovered")]

    component       = models.CharField(max_length=25, choices=COMPONENT)
    component_id    = models.CharField(max_length=100)
    status          = models.CharField(max_length=10, choices=STATUS, default="HEALTHY")
    health_score    = models.FloatField(default=100.0)
    last_checked    = models.DateTimeField(auto_now=True)
    latency_ms      = models.IntegerField(default=0)
    error_rate      = models.FloatField(default=0.0)
    uptime_percent  = models.FloatField(default=100.0)
    auto_healed     = models.BooleanField(default=False)
    heal_actions    = models.JSONField(default=list)
    metadata        = models.JSONField(default=dict)

    class Meta:
        db_table = "tap_infra_health"
        ordering = ["health_score"]

    def __str__(self): return f"{self.component} [{self.status}] health:{self.health_score:.0f}%"

    @property
    def status_color(self):
        return {"HEALTHY":"#10b981","DEGRADED":"#f59e0b","CRITICAL":"#ef4444","HEALING":"#00d4ff","OFFLINE":"#6b7280","RECOVERED":"#8b5cf6"}.get(self.status,"#6b7280")


class HealingEvent(models.Model):
    ACTION_TYPE = [("REROUTE","Evidence Rerouted"),("RESTORE","Storage Restored"),
                   ("FAILOVER","Chain Failover"),("REPIN","IPFS Re-pinned"),
                   ("REINDEX","Index Rebuilt"),("BRIDGE","Cross-Chain Bridge"),
                   ("BACKUP_NODE","Backup Node Activated"),("CONSENSUS","Consensus Repair")]

    component       = models.ForeignKey(InfrastructureHealth, on_delete=models.CASCADE, related_name="events")
    action_type     = models.CharField(max_length=20, choices=ACTION_TYPE)
    triggered_at    = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    success         = models.BooleanField(default=True)
    evidence_affected = models.IntegerField(default=0)
    description     = models.TextField()
    auto_triggered  = models.BooleanField(default=True)
    triggered_by    = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    recovery_time_seconds = models.IntegerField(default=0)

    class Meta:
        db_table = "tap_healing_events"
        ordering = ["-triggered_at"]

    def __str__(self): return f"{self.action_type} on {self.component.component_id} [{'OK' if self.success else 'FAIL'}]"

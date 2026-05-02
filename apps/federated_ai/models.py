"""TAP-DEV Phase 4 — Federated Learning AI Models"""
import uuid
from django.db import models


class FederatedModel(models.Model):
    """Global model state that aggregates encrypted updates from orgs."""
    STATUS = [('INITIALIZING','Initializing'),('AGGREGATING','Aggregating'),('STABLE','Stable'),('OUTDATED','Outdated')]
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version        = models.CharField(max_length=30)
    status         = models.CharField(max_length=20, choices=STATUS, default='STABLE')
    global_accuracy = models.FloatField(default=0.0)
    global_f1      = models.FloatField(default=0.0)
    participating_orgs = models.IntegerField(default=0)
    rounds_completed = models.IntegerField(default=0)
    created_at     = models.DateTimeField(auto_now_add=True)
    last_aggregated = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = 'tap_fed_models'
    def __str__(self): return f"FedModel {self.version} [{self.status}]"


class FederatedUpdate(models.Model):
    """Encrypted gradient update from a participating organization."""
    STATUS = [('PENDING','Pending'),('VALIDATED','Validated'),('AGGREGATED','Aggregated'),('REJECTED','Rejected')]
    federated_model = models.ForeignKey(FederatedModel, on_delete=models.CASCADE, related_name='updates')
    organization    = models.ForeignKey('tap_org.Organization', on_delete=models.CASCADE)
    round_number    = models.IntegerField()
    local_accuracy  = models.FloatField()
    local_f1        = models.FloatField()
    samples_trained = models.IntegerField()
    update_hash     = models.CharField(max_length=64)
    encrypted_payload = models.TextField(blank=True)
    status          = models.CharField(max_length=15, choices=STATUS, default='PENDING')
    submitted_at    = models.DateTimeField(auto_now_add=True)
    dp_epsilon      = models.FloatField(default=1.0)  # differential privacy budget
    class Meta:
        db_table = 'tap_fed_updates'
    def __str__(self): return f"Update from {self.organization.name} round {self.round_number}"

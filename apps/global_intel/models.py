"""TAP-DEV Phase 5 — Global Intelligence & Threat Map"""
import uuid
from django.db import models


class GlobalThreatEvent(models.Model):
    THREAT_TYPE = [("ATTACK","Cyberattack"),("BREACH","Data Breach"),("RANSOMWARE","Ransomware"),
                   ("APT","APT Activity"),("INSIDER","Insider Threat"),("FRAUD","Document Fraud"),
                   ("IOT","IoT Attack"),("CRITICAL_INFRA","Critical Infrastructure")]

    event_id    = models.UUIDField(default=uuid.uuid4, unique=True)
    threat_type = models.CharField(max_length=20, choices=THREAT_TYPE)
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    severity    = models.CharField(max_length=10, default="MEDIUM")
    country     = models.CharField(max_length=80)
    city        = models.CharField(max_length=80, blank=True)
    geo_lat     = models.FloatField()
    geo_lon     = models.FloatField()
    reported_at = models.DateTimeField(auto_now_add=True)
    is_active   = models.BooleanField(default=True)
    source      = models.CharField(max_length=50, default="TAP-DEV")
    affected_sectors = models.JSONField(default=list)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "tap_global_threats"
        ordering = ["-reported_at"]

    def __str__(self): return f"[{self.threat_type}] {self.title} — {self.country}"

    @property
    def severity_color(self):
        return {"CRITICAL":"#dc2626","HIGH":"#ef4444","MEDIUM":"#f59e0b","LOW":"#84cc16"}.get(self.severity,"#6b7280")


class TranslationRequest(models.Model):
    STATUS = [("PENDING","Pending"),("COMPLETE","Complete"),("FAILED","Failed")]

    source_text     = models.TextField()
    source_language = models.CharField(max_length=10)
    target_language = models.CharField(max_length=10)
    translated_text = models.TextField(blank=True)
    status          = models.CharField(max_length=10, choices=STATUS, default="PENDING")
    created_at      = models.DateTimeField(auto_now_add=True)
    model_used      = models.CharField(max_length=50, default="tapdev-translate-v5")
    evidence_ref    = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "tap_translations"
        ordering = ["-created_at"]

    def __str__(self): return f"Translation {self.source_language}→{self.target_language} [{self.status}]"

"""TAP-DEV Phase 5 — Global Threat Intelligence Sharing"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class ThreatSignature(models.Model):
    THREAT_CLASS = [("MALWARE","Malware"),("RANSOMWARE","Ransomware"),("APT","APT"),
                    ("PHISHING","Phishing"),("INSIDER","Insider Threat"),("ZERO_DAY","Zero-Day"),
                    ("SUPPLY_CHAIN","Supply Chain"),("DEEPFAKE","Deepfake Document"),("IOT_ATTACK","IoT Attack")]
    CONFIDENCE = [(1,"Low"),(2,"Medium"),(3,"High"),(4,"Verified"),(5,"Confirmed Critical")]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    threat_class    = models.CharField(max_length=20, choices=THREAT_CLASS)
    ioc_type        = models.CharField(max_length=30)   # IP, hash, domain, pattern
    ioc_value_hash  = models.CharField(max_length=64)   # anonymized hash of actual IOC
    description     = models.TextField()
    confidence      = models.IntegerField(choices=CONFIDENCE, default=2)
    severity        = models.CharField(max_length=10, default="MEDIUM")
    contributed_by  = models.ForeignKey("tap_org.Organization", null=True, on_delete=models.SET_NULL)
    contributed_at  = models.DateTimeField(auto_now_add=True)
    is_anonymous    = models.BooleanField(default=True)
    global_matches  = models.IntegerField(default=0)
    verified_by_nodes = models.IntegerField(default=0)
    stix_json       = models.JSONField(default=dict)  # STIX 2.1 format
    ttps            = models.JSONField(default=list)  # MITRE ATT&CK TTPs
    mitre_tactics   = models.JSONField(default=list)

    class Meta:
        db_table = "tap_threat_signatures"
        ordering = ["-contributed_at"]

    def __str__(self): return f"{self.threat_class} [{self.severity}] matches:{self.global_matches}"

    @property
    def confidence_label(self): return dict(self.CONFIDENCE).get(self.confidence, "Unknown")


class ThreatFeed(models.Model):
    """Real-time threat feed from global consortium nodes."""
    FEED_SOURCE = [("CONSORTIUM","Global Consortium"),("CERT","National CERT"),
                   ("INTERPOL","INTERPOL"),("MITRE","MITRE ATT&CK"),("ISA","ISAC"),("TAP_AI","TAP-DEV AI")]

    feed_source   = models.CharField(max_length=20, choices=FEED_SOURCE)
    title         = models.CharField(max_length=200)
    description   = models.TextField()
    severity      = models.CharField(max_length=10)
    published_at  = models.DateTimeField(auto_now_add=True)
    affected_sectors = models.JSONField(default=list)
    affected_countries = models.JSONField(default=list)
    signatures    = models.ManyToManyField(ThreatSignature, blank=True)
    is_active     = models.BooleanField(default=True)

    class Meta:
        db_table = "tap_threat_feeds"
        ordering = ["-published_at"]

    def __str__(self): return f"[{self.feed_source}] {self.title}"

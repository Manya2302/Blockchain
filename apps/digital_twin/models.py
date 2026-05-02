"""TAP-DEV Phase 5 — Digital Twin Simulation"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class DigitalTwin(models.Model):
    TWIN_TYPE = [("NETWORK","Network Infrastructure"),("CLOUD","Cloud Environment"),
                 ("INDUSTRIAL","Industrial ICS/SCADA"),("HOSPITAL","Hospital Systems"),
                 ("SMART_CITY","Smart City"),("AIRPORT","Airport Systems"),("MILITARY","Defense Network")]
    STATUS = [("IDLE","Idle"),("RUNNING","Simulation Running"),("PAUSED","Paused"),("COMPLETE","Complete"),("ERROR","Error")]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=200)
    twin_type   = models.CharField(max_length=15, choices=TWIN_TYPE)
    status      = models.CharField(max_length=10, choices=STATUS, default="IDLE")
    organization = models.ForeignKey("tap_org.Organization", null=True, on_delete=models.SET_NULL)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    topology    = models.JSONField(default=dict)  # network topology definition
    assets      = models.JSONField(default=list)  # virtual assets
    vulnerabilities = models.JSONField(default=list)
    total_simulations = models.IntegerField(default=0)
    last_simulation = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tap_digital_twins"
        ordering = ["-created_at"]

    def __str__(self): return f"{self.name} [{self.twin_type}] — {self.status}"


class TwinSimulation(models.Model):
    ATTACK_SCENARIO = [("RANSOMWARE","Ransomware Attack"),("DDoS","DDoS Flood"),
                       ("APT_LATERAL","APT Lateral Movement"),("SUPPLY_CHAIN","Supply Chain Compromise"),
                       ("INSIDER","Insider Data Theft"),("ZERO_DAY","Zero-Day Exploit"),
                       ("PHISHING","Spear Phishing"),("IOT_PIVOT","IoT Pivot Attack")]
    STATUS = [("QUEUED","Queued"),("RUNNING","Running"),("COMPLETE","Complete"),("FAILED","Failed")]

    twin        = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name="simulations")
    attack_scenario = models.CharField(max_length=20, choices=ATTACK_SCENARIO)
    status      = models.CharField(max_length=10, choices=STATUS, default="QUEUED")
    started_at  = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    duration_seconds = models.IntegerField(default=0)
    detection_time = models.IntegerField(default=0)  # seconds to detect
    was_detected = models.BooleanField(null=True)
    ai_response_score = models.FloatField(default=0.0)
    kill_chain_steps = models.JSONField(default=list)
    affected_assets = models.JSONField(default=list)
    evidence_generated = models.JSONField(default=list)
    report_data = models.JSONField(default=dict)

    class Meta:
        db_table = "tap_twin_simulations"
        ordering = ["-started_at"]

    def __str__(self): return f"{self.attack_scenario} on {self.twin.name} [{self.status}]"

    @property
    def detection_rate_label(self):
        if self.was_detected is None: return "Pending"
        return f"Detected in {self.detection_time}s" if self.was_detected else "Evaded"

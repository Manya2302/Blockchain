"""TAP-DEV Phase 5 — Autonomous AI Investigation Engine"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class AIInvestigation(models.Model):
    """Fully autonomous AI-driven forensic investigation."""
    STATUS = [('INITIALIZING','Initializing'),('ANALYZING','Analyzing'),('GENERATING','Generating Report'),
              ('COMPLETE','Complete'),('ESCALATED','Escalated to Human'),('ARCHIVED','Archived')]
    INVESTIGATION_TYPE = [
        ('TIMELINE_ANOMALY','Timeline Anomaly'),('ATTACKER_PATTERN','Attacker Pattern'),
        ('INSIDER_THREAT','Insider Threat'),('COORDINATED_ATTACK','Coordinated Attack'),
        ('DATA_EXFIL','Data Exfiltration'),('SUPPLY_CHAIN','Supply Chain Attack'),
        ('RANSOMWARE','Ransomware Campaign'),('APT','Advanced Persistent Threat'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation_type = models.CharField(max_length=25, choices=INVESTIGATION_TYPE)
    status          = models.CharField(max_length=20, choices=STATUS, default='INITIALIZING')
    title           = models.CharField(max_length=300)
    triggered_by    = models.CharField(max_length=50, default='AUTO')
    triggered_user  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    evidence_scope  = models.JSONField(default=list)    # evidence IDs in scope
    started_at      = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    # AI model outputs
    confidence_score    = models.FloatField(default=0.0)
    threat_level        = models.CharField(max_length=15, default='UNKNOWN')
    narrative           = models.TextField(blank=True)        # LLM-generated
    attacker_profile    = models.JSONField(default=dict)
    attack_timeline     = models.JSONField(default=list)
    recommended_actions = models.JSONField(default=list)
    legal_citations     = models.JSONField(default=list)
    ioc_list            = models.JSONField(default=list)      # indicators of compromise
    graph_data          = models.JSONField(default=dict)      # GNN output
    organization        = models.ForeignKey('tap_org.Organization', null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'tap_ai_investigations'
        ordering = ['-started_at']

    def __str__(self): return f"Investigation [{self.investigation_type}] — {self.title[:60]}"

    @property
    def threat_color(self):
        return {'CRITICAL':'#dc2626','HIGH':'#ef4444','MEDIUM':'#f59e0b','LOW':'#84cc16','UNKNOWN':'#6b7280'}.get(self.threat_level,'#6b7280')


class ForensicNarrative(models.Model):
    """LLM-generated forensic narratives and legal summaries."""
    NARRATIVE_TYPE = [('INVESTIGATION','Investigation Summary'),('LEGAL','Legal Report'),
                      ('INCIDENT','Incident Report'),('EXECUTIVE','Executive Brief'),
                      ('COURT','Court-Ready Document'),('INSURANCE','Insurance Claim')]

    investigation   = models.ForeignKey(AIInvestigation, on_delete=models.CASCADE, related_name='narratives')
    narrative_type  = models.CharField(max_length=20, choices=NARRATIVE_TYPE)
    title           = models.CharField(max_length=200)
    content         = models.TextField()
    language        = models.CharField(max_length=10, default='en')
    word_count      = models.IntegerField(default=0)
    generated_at    = models.DateTimeField(auto_now_add=True)
    model_used      = models.CharField(max_length=50, default='tapdev-llm-v5')
    confidence      = models.FloatField(default=0.0)
    jurisdictions   = models.JSONField(default=list)  # applicable legal jurisdictions
    is_translated   = models.BooleanField(default=False)
    source_language = models.CharField(max_length=10, blank=True)

    class Meta:
        db_table = 'tap_forensic_narratives'
        ordering = ['-generated_at']

    def __str__(self): return f"{self.get_narrative_type_display()}: {self.title[:60]}"

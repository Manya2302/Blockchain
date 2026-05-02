"""TAP-DEV Phase 5 — Autonomous Legal Document AI"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class LegalDocument(models.Model):
    DOC_TYPE = [("COURT_REPORT","Court-Ready Report"),("INCIDENT_REPORT","Incident Report"),
                ("INSURANCE_CLAIM","Insurance Claim"),("COMPLIANCE_CERT","Compliance Certificate"),
                ("LEGAL_BRIEF","Legal Brief"),("CHAIN_OF_CUSTODY","Chain of Custody"),
                ("EXPERT_TESTIMONY","Expert Testimony"),("GDPR_BREACH","GDPR Breach Notification")]
    STATUS = [("DRAFT","Draft"),("REVIEW","Under Review"),("APPROVED","Approved"),("FILED","Filed"),("REJECTED","Rejected")]
    JURISDICTION = [("US","United States"),("EU","European Union"),("UK","United Kingdom"),
                    ("CA","Canada"),("AU","Australia"),("IN","India"),("SG","Singapore"),("INTL","International")]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doc_type        = models.CharField(max_length=25, choices=DOC_TYPE)
    title           = models.CharField(max_length=300)
    status          = models.CharField(max_length=10, choices=STATUS, default="DRAFT")
    jurisdiction    = models.CharField(max_length=10, choices=JURISDICTION, default="INTL")
    language        = models.CharField(max_length=10, default="en")
    evidence_refs   = models.JSONField(default=list)
    investigation   = models.ForeignKey("tap_autoai.AIInvestigation", null=True, blank=True, on_delete=models.SET_NULL)
    generated_by_ai = models.BooleanField(default=True)
    ai_model_used   = models.CharField(max_length=50, default="tapdev-legal-ai-v5")
    generated_at    = models.DateTimeField(auto_now_add=True)
    generated_by    = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    approved_by     = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_docs")
    approved_at     = models.DateTimeField(null=True, blank=True)
    content         = models.TextField()
    summary         = models.TextField(blank=True)
    legal_citations = models.JSONField(default=list)
    blockchain_proof = models.CharField(max_length=100, blank=True)
    word_count      = models.IntegerField(default=0)
    page_count      = models.IntegerField(default=1)
    digital_signature = models.CharField(max_length=128, blank=True)
    organization    = models.ForeignKey("tap_org.Organization", null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "tap_legal_documents"
        ordering = ["-generated_at"]

    def __str__(self): return f"{self.get_doc_type_display()}: {self.title[:60]}"

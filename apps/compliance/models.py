"""TAP-DEV Phase 4 — Compliance Management Models"""
from django.db import models
from django.contrib.auth.models import User


class ComplianceFramework(models.Model):
    FRAMEWORK_CHOICES = [
        ('GDPR','GDPR'),('HIPAA','HIPAA'),('ISO27001','ISO 27001'),('SOC2','SOC 2'),
        ('PCI_DSS','PCI DSS'),('NIST','NIST CSF'),('ISO27701','ISO 27701'),('CCPA','CCPA'),
    ]
    name        = models.CharField(max_length=30, choices=FRAMEWORK_CHOICES, unique=True)
    full_name   = models.CharField(max_length=100)
    description = models.TextField()
    version     = models.CharField(max_length=20, blank=True)
    controls    = models.JSONField(default=list)  # list of control objects
    is_active   = models.BooleanField(default=True)
    class Meta:
        db_table = 'tap_compliance_frameworks'
    def __str__(self): return self.full_name


class ComplianceAssessment(models.Model):
    STATUS_CHOICES = [('IN_PROGRESS','In Progress'),('COMPLETED','Completed'),('FAILED','Failed'),('REMEDIATION','Remediation')]

    organization = models.ForeignKey('tap_org.Organization', on_delete=models.CASCADE, related_name='compliance_assessments')
    framework    = models.ForeignKey(ComplianceFramework, on_delete=models.CASCADE)
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    started_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status       = models.CharField(max_length=15, choices=STATUS_CHOICES, default='IN_PROGRESS')
    overall_score = models.FloatField(default=0.0)  # 0-100
    findings     = models.JSONField(default=list)
    remediation_plan = models.TextField(blank=True)
    next_assessment = models.DateField(null=True, blank=True)
    cert_issued  = models.BooleanField(default=False)

    class Meta:
        db_table = 'tap_compliance_assessments'
        ordering = ['-started_at']

    def __str__(self): return f"{self.organization.name} — {self.framework.name} [{self.status}]"

    @property
    def score_color(self):
        if self.overall_score >= 90: return '#10b981'
        if self.overall_score >= 70: return '#f59e0b'
        return '#ef4444'

    @property
    def compliance_grade(self):
        if self.overall_score >= 95: return 'A+'
        if self.overall_score >= 90: return 'A'
        if self.overall_score >= 80: return 'B'
        if self.overall_score >= 70: return 'C'
        return 'F'


class ComplianceControl(models.Model):
    STATUS_CHOICES = [('COMPLIANT','Compliant'),('PARTIAL','Partial'),('NON_COMPLIANT','Non-Compliant'),('NA','N/A')]
    assessment   = models.ForeignKey(ComplianceAssessment, on_delete=models.CASCADE, related_name='controls')
    control_id   = models.CharField(max_length=30)
    control_name = models.CharField(max_length=200)
    status       = models.CharField(max_length=15, choices=STATUS_CHOICES, default='NON_COMPLIANT')
    score        = models.FloatField(default=0.0)
    evidence_refs = models.JSONField(default=list)
    notes        = models.TextField(blank=True)
    class Meta:
        db_table = 'tap_compliance_controls'
    def __str__(self): return f"{self.control_id}: {self.control_name[:50]}"

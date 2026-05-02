"""
TAP-DEV Phase 4 — Multi-Tenant Organization Models
"""
import uuid, hashlib, secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Organization(models.Model):
    ORG_TYPE_CHOICES = [
        ('LAW_FIRM','Law Firm'),('ENTERPRISE','Enterprise'),('CYBERSEC','Cybersecurity'),
        ('FORENSIC_LAB','Forensic Lab'),('HOSPITAL','Hospital'),('GOVERNMENT','Government'),
        ('INSURANCE','Insurance'),('BANK','Bank'),('EDUCATION','Education'),('OTHER','Other'),
    ]
    STATUS_CHOICES = [('ACTIVE','Active'),('SUSPENDED','Suspended'),('TRIAL','Trial'),('PENDING','Pending')]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=200, unique=True)
    slug            = models.SlugField(max_length=80, unique=True)
    org_type        = models.CharField(max_length=20, choices=ORG_TYPE_CHOICES, default='ENTERPRISE')
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='TRIAL')
    logo            = models.ImageField(upload_to='org_logos/', null=True, blank=True)
    website         = models.URLField(blank=True)
    country         = models.CharField(max_length=80, blank=True)
    city            = models.CharField(max_length=80, blank=True)
    contact_email   = models.EmailField()
    created_at      = models.DateTimeField(auto_now_add=True)
    created_by      = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='orgs_created')
    max_users       = models.IntegerField(default=10)
    max_evidence_gb = models.FloatField(default=5.0)
    api_quota_daily = models.IntegerField(default=1000)
    org_settings    = models.JSONField(default=dict)

    class Meta:
        db_table = 'tap_organizations'
        ordering = ['name']

    def __str__(self): return self.name

    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()


class OrganizationMembership(models.Model):
    ROLE_CHOICES = [
        ('SUPER_ADMIN','Super Admin'),('ORG_ADMIN','Org Admin'),('ANALYST','Analyst'),
        ('INVESTIGATOR','Investigator'),('AUDITOR','Auditor'),('LEGAL_REVIEWER','Legal Reviewer'),
        ('SUBMITTER','Submitter'),
    ]
    ROLE_PERMS = {
        'SUPER_ADMIN':    ['all'],
        'ORG_ADMIN':      ['manage_users','manage_evidence','view_analytics','manage_billing','view_soc','run_simulations'],
        'ANALYST':        ['view_evidence','analyze_evidence','view_ai','view_graph','view_anomalies'],
        'INVESTIGATOR':   ['view_evidence','analyze_evidence','view_ai','run_simulations','export_reports'],
        'AUDITOR':        ['view_evidence','view_audit_logs','view_compliance','export_reports'],
        'LEGAL_REVIEWER': ['view_evidence','view_reports','verify_zkp','export_reports'],
        'SUBMITTER':      ['upload_evidence','view_own_evidence'],
    }
    ROLE_COLORS = {
        'SUPER_ADMIN':'#dc2626','ORG_ADMIN':'#8b5cf6','ANALYST':'#00d4ff',
        'INVESTIGATOR':'#f59e0b','AUDITOR':'#10b981','LEGAL_REVIEWER':'#06b6d4','SUBMITTER':'#6b7280',
    }

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='org_memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='SUBMITTER')
    is_active    = models.BooleanField(default=True)
    joined_at    = models.DateTimeField(auto_now_add=True)
    invited_by   = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='invitations_sent')
    department   = models.CharField(max_length=100, blank=True)
    job_title    = models.CharField(max_length=100, blank=True)
    extra_perms  = models.JSONField(default=list)

    class Meta:
        db_table = 'tap_org_memberships'
        unique_together = ('user', 'organization')

    def __str__(self): return f"{self.user.username}@{self.organization.name}[{self.role}]"

    def has_permission(self, perm):
        rp = self.ROLE_PERMS.get(self.role, [])
        return 'all' in rp or perm in rp or perm in self.extra_perms

    @property
    def role_color(self): return self.ROLE_COLORS.get(self.role, '#6b7280')


class APIKey(models.Model):
    SCOPE_CHOICES = [('READ','Read'),('WRITE','Write'),('ADMIN','Admin'),('IOT','IoT'),('MOBILE','Mobile')]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='api_keys')
    name         = models.CharField(max_length=100)
    key_prefix   = models.CharField(max_length=8)
    key_hash     = models.CharField(max_length=64)
    scope        = models.CharField(max_length=15, choices=SCOPE_CHOICES, default='READ')
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at   = models.DateTimeField(auto_now_add=True)
    last_used    = models.DateTimeField(null=True, blank=True)
    requests_count = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'tap_api_keys'

    def __str__(self): return f"{self.key_prefix}...[{self.scope}]@{self.organization.name}"

    @staticmethod
    def generate():
        raw = secrets.token_urlsafe(32)
        return raw, raw[:8], hashlib.sha256(raw.encode()).hexdigest()

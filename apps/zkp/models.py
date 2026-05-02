"""TAP-DEV Phase 4+ — Zero-Knowledge Proof Engine Models (Enhanced)
Adds Resume/Credential verification system with trusted issuers."""
import hashlib, secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ZKPVerification(models.Model):
    """A ZKP-based document authenticity proof (privacy-preserving)."""
    STATUS_CHOICES = [('PENDING','Pending'),('VALID','Valid'),('INVALID','Invalid'),('EXPIRED','Expired')]
    USE_CASE = [
        ('DOCUMENT_AUTH','Document Authenticity'),('CREDENTIAL','Credential Verification'),
        ('MEDICAL_RECORD','Medical Record'),('LEGAL_CERT','Legal Certificate'),
        ('EDUCATION','Educational Credential'),('CORPORATE','Corporate Compliance'),
        ('RESUME','Resume Verification'),('SKILL_CERT','Skill Certification'),
    ]

    evidence        = models.ForeignKey('tap_evidence.Evidence', on_delete=models.CASCADE, related_name='zkp_proofs')
    use_case        = models.CharField(max_length=20, choices=USE_CASE, default='DOCUMENT_AUTH')
    proof_id        = models.CharField(max_length=64, unique=True)
    commitment      = models.CharField(max_length=128)  # public commitment (hash of hash)
    nullifier       = models.CharField(max_length=64)   # prevents replay
    public_inputs   = models.JSONField(default=dict)    # non-sensitive disclosed fields
    proof_circuit   = models.CharField(max_length=50, default='groth16-sha256')
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_by      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='zkp_created')
    created_at      = models.DateTimeField(auto_now_add=True)
    verified_at     = models.DateTimeField(null=True, blank=True)
    verified_by     = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='zkp_verified')
    expires_at      = models.DateTimeField(null=True, blank=True)
    qr_code_data    = models.TextField(blank=True)
    verification_url = models.URLField(blank=True)
    organization    = models.ForeignKey('tap_org.Organization', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'tap_zkp_verifications'
        ordering = ['-created_at']

    def __str__(self): return f"ZKP#{self.proof_id[:12]}[{self.use_case}]"

    @staticmethod
    def generate_proof_id(evidence_hash):
        return hashlib.sha256(f"{evidence_hash}{secrets.token_hex(16)}".encode()).hexdigest()

    @staticmethod
    def generate_commitment(evidence_hash):
        """Double-hash for ZK commitment scheme (simplified Pedersen-style)."""
        salt = secrets.token_hex(32)
        return hashlib.sha256(f"{evidence_hash}{salt}".encode()).hexdigest(), salt

    def is_valid(self):
        if self.status != 'VALID': return False
        if self.expires_at and self.expires_at < timezone.now(): return False
        return True

    @property
    def status_color(self):
        return {'PENDING':'#f59e0b','VALID':'#10b981','INVALID':'#ef4444','EXPIRED':'#6b7280'}.get(self.status,'#6b7280')


class TrustedIssuer(models.Model):
    """
    A trusted issuer of credentials (university, certification body, employer).
    Used to validate resume credentials against known issuers.
    """
    ISSUER_TYPE = [
        ('UNIVERSITY', 'University/College'),
        ('CERTIFICATION', 'Certification Body'),
        ('EMPLOYER', 'Employer'),
        ('GOVERNMENT', 'Government Agency'),
        ('PROFESSIONAL', 'Professional Body'),
    ]
    TRUST_LEVEL = [
        ('VERIFIED', 'Verified'),
        ('TRUSTED', 'Trusted'),
        ('PENDING', 'Pending Verification'),
        ('REVOKED', 'Revoked'),
    ]

    name            = models.CharField(max_length=255)
    issuer_type     = models.CharField(max_length=20, choices=ISSUER_TYPE, default='UNIVERSITY')
    trust_level     = models.CharField(max_length=10, choices=TRUST_LEVEL, default='PENDING')
    issuer_hash     = models.CharField(max_length=64, unique=True)  # SHA-256 of issuer identity
    public_key      = models.TextField(blank=True)  # Issuer's public commitment key
    website         = models.URLField(blank=True)
    country         = models.CharField(max_length=100, blank=True)
    description     = models.TextField(blank=True)
    verified_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    created_by      = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'tap_trusted_issuers'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.trust_level}]"

    @staticmethod
    def compute_issuer_hash(name, issuer_type):
        raw = f"{name.strip().lower()}:{issuer_type}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @property
    def trust_color(self):
        return {
            'VERIFIED': '#10b981', 'TRUSTED': '#3b82f6',
            'PENDING': '#f59e0b', 'REVOKED': '#ef4444',
        }.get(self.trust_level, '#6b7280')


class ResumeCredential(models.Model):
    """
    A single credential claim within a resume verification workflow.
    e.g., 'User holds a Bachelor's degree from MIT'
    """
    CLAIM_TYPE = [
        ('DEGREE', 'Academic Degree'),
        ('DIPLOMA', 'Diploma'),
        ('CERTIFICATION', 'Professional Certification'),
        ('SKILL', 'Verified Skill'),
        ('EMPLOYMENT', 'Employment History'),
        ('LICENSE', 'Professional License'),
    ]
    STATUS = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'Expired'),
    ]

    owner           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resume_credentials')
    claim_type      = models.CharField(max_length=20, choices=CLAIM_TYPE, default='DEGREE')
    claim_title     = models.CharField(max_length=255)  # e.g., "Bachelor of Computer Science"
    claim_detail    = models.TextField(blank=True)       # Additional non-sensitive details
    issuer          = models.ForeignKey(TrustedIssuer, null=True, blank=True, on_delete=models.SET_NULL)
    issuer_name     = models.CharField(max_length=255, blank=True)  # Fallback if no TrustedIssuer

    # ZKP linkage
    evidence        = models.ForeignKey(
        'tap_evidence.Evidence', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='resume_credentials'
    )
    zkp_proof       = models.ForeignKey(
        ZKPVerification, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='credentials'
    )

    # Cryptographic commitment (hash of the original document)
    document_hash   = models.CharField(max_length=64, blank=True)
    commitment      = models.CharField(max_length=128, blank=True)
    commitment_salt = models.CharField(max_length=64, blank=True)  # Never exposed

    # Verification
    status          = models.CharField(max_length=10, choices=STATUS, default='PENDING')
    verified_at     = models.DateTimeField(null=True, blank=True)
    verified_by     = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='verified_credentials'
    )
    expires_at      = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tap_resume_credentials'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.claim_title} [{self.status}]"

    def generate_commitment(self):
        """Generate cryptographic commitment for this credential."""
        if not self.document_hash:
            return
        salt = secrets.token_hex(32)
        raw = f"{self.document_hash}:{self.claim_type}:{self.claim_title}:{salt}"
        self.commitment = hashlib.sha256(raw.encode()).hexdigest()
        self.commitment_salt = salt

    def verify_against_issuer(self):
        """Check if this credential's issuer is trusted."""
        if not self.issuer:
            return False
        return self.issuer.trust_level in ('VERIFIED', 'TRUSTED')

    @property
    def status_color(self):
        return {
            'PENDING': '#f59e0b', 'VERIFIED': '#10b981',
            'FAILED': '#ef4444', 'EXPIRED': '#6b7280',
        }.get(self.status, '#6b7280')


class VerificationLog(models.Model):
    """Audit log for all verification attempts."""
    ACTION_CHOICES = [
        ('SUBMIT', 'Credential Submitted'),
        ('VERIFY', 'Verification Attempt'),
        ('APPROVE', 'Approved'),
        ('REJECT', 'Rejected'),
        ('EXPIRE', 'Expired'),
        ('REVOKE', 'Revoked'),
    ]

    credential      = models.ForeignKey(
        ResumeCredential, null=True, blank=True,
        on_delete=models.CASCADE, related_name='verification_logs'
    )
    zkp_proof       = models.ForeignKey(
        ZKPVerification, null=True, blank=True,
        on_delete=models.CASCADE, related_name='verification_logs'
    )
    action          = models.CharField(max_length=10, choices=ACTION_CHOICES)
    actor           = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)
    detail          = models.TextField(blank=True)
    success         = models.BooleanField(default=True)
    timestamp       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tap_verification_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"VerifyLog [{self.action}] {self.timestamp}"

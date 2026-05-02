"""
TAP-DEV Phase 2+ — Evidence Models
Adds: version history, IPFS-ready, blockchain-ready, status notifications,
      self-destructing documents (expiry policy).
"""
import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import get_valid_filename


def evidence_upload_path(instance, filename):
    from django.utils import timezone
    now = timezone.now()
    safe_name = get_valid_filename(filename.rsplit('/', 1)[-1].rsplit('\\', 1)[-1])
    return f"evidence/{now.year}/{now.month:02d}/{now.day:02d}/{safe_name}"


class Evidence(models.Model):
    STATUS_CHOICES = [
        ('PENDING','Pending'),('VERIFIED','Verified'),
        ('FLAGGED','Flagged'),('STORED','Stored'),('ARCHIVED','Archived'),
    ]
    EXPIRY_TYPE_CHOICES = [
        ('NONE', 'No Expiry'),
        ('TIMED', 'Time-Based'),
        ('EVENT', 'Event-Based'),
    ]

    title             = models.CharField(max_length=255)
    description       = models.TextField(blank=True)
    file              = models.FileField(upload_to=evidence_upload_path, null=True, blank=True)
    filename_original = models.CharField(max_length=255, blank=True)
    file_size         = models.BigIntegerField(default=0)
    mime_type         = models.CharField(max_length=100, blank=True)
    sha256_hash       = models.CharField(max_length=64, db_index=True)
    uploader          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_evidence')
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    trust_score       = models.IntegerField(default=100)
    ipfs_cid          = models.CharField(max_length=255, blank=True)
    blockchain_tx     = models.CharField(max_length=255, blank=True)
    case_id           = models.CharField(max_length=100, blank=True, db_index=True)
    tags              = models.CharField(max_length=255, blank=True)
    version           = models.PositiveIntegerField(default=1)
    is_latest_version = models.BooleanField(default=True)
    parent_evidence   = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='versions')

    # ── Self-Destructing Documents (Expiry Policy) ─────────────────
    expiry_enabled    = models.BooleanField(default=False)
    expiry_type       = models.CharField(max_length=10, choices=EXPIRY_TYPE_CHOICES, default='NONE')
    expires_at        = models.DateTimeField(null=True, blank=True, db_index=True)
    expiry_condition  = models.CharField(max_length=255, blank=True)  # For event-based
    is_expired        = models.BooleanField(default=False, db_index=True)
    expired_at        = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tap_evidence'
        ordering = ['-created_at']

    def __str__(self): return f"[{self.id}] {self.title} v{self.version}"

    def get_status_class(self):
        return {'PENDING':'status-pending','VERIFIED':'status-verified',
                'FLAGGED':'status-flagged','STORED':'status-stored',
                'ARCHIVED':'status-archived'}.get(self.status,'')

    def get_trust_class(self):
        if self.trust_score >= 80: return 'trust-high'
        if self.trust_score >= 50: return 'trust-medium'
        return 'trust-low'

    def get_trust_label(self):
        if self.trust_score >= 80: return 'Trusted'
        if self.trust_score >= 50: return 'Moderate'
        if self.trust_score >= 25: return 'Suspicious'
        return 'Compromised'

    @property
    def file_size_display(self):
        s = self.file_size
        for unit in ['B','KB','MB','GB']:
            if s < 1024: return f"{s:.1f} {unit}"
            s /= 1024
        return f"{s:.1f} TB"

    @property
    def is_blockchain_anchored(self): return bool(self.blockchain_tx)
    @property
    def is_ipfs_pinned(self): return bool(self.ipfs_cid)

    @property
    def expiry_status(self):
        """Get expiry status dict for UI display."""
        from .expiry_engine import ExpiryEngine
        return ExpiryEngine(self).get_expiry_status()

    @property
    def is_content_accessible(self):
        """Check if document content is still accessible (not expired)."""
        return not self.is_expired and self.file

    @staticmethod
    def compute_sha256(file_obj):
        h = hashlib.sha256()
        for chunk in file_obj.chunks(): h.update(chunk)
        file_obj.seek(0)
        return h.hexdigest()

    def get_all_versions(self):
        """Return all versions of this evidence chain."""
        root = self
        while root.parent_evidence:
            root = root.parent_evidence
        return Evidence.objects.filter(
            models.Q(pk=root.pk) | models.Q(parent_evidence=root)
        ).order_by('version')

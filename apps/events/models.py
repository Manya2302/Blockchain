"""
TAP-DEV Events App — Event Chain Model
Each event points to the previous event, forming a tamper-evident linked chain.
event_hash = SHA-256(event_type + timestamp + actor_id + previous_hash + evidence_id)
This chain is the foundation for future Blockchain anchoring (Phase 2).
"""
import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Event(models.Model):
    EVENT_TYPES = [
        ('UPLOAD', 'Upload'),
        ('MODIFY', 'Modify'),
        ('VERIFY', 'Verify'),
        ('STORE',  'Store'),
        ('FLAG',   'Flag'),
        ('NOTE',   'Note'),
        ('EXPIRE_SET', 'Expiry Set'),
        ('EXPIRED', 'Expired'),
    ]

    EVENT_COLORS = {
        'UPLOAD': '#00d4ff',
        'MODIFY': '#f59e0b',
        'VERIFY': '#10b981',
        'STORE':  '#8b5cf6',
        'FLAG':   '#ef4444',
        'NOTE':   '#6b7280',
        'EXPIRE_SET': '#f97316',
        'EXPIRED': '#991b1b',
    }

    evidence       = models.ForeignKey('tap_evidence.Evidence', on_delete=models.CASCADE, related_name='events')
    event_type     = models.CharField(max_length=20, choices=EVENT_TYPES)
    timestamp      = models.DateTimeField(default=timezone.now, db_index=True)
    actor          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='events')
    description    = models.TextField(blank=True)
    # Self-referential FK: the chain link
    previous_event = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='next_events'
    )
    # Cryptographic chain hash (SHA-256 of this event + previous hash)
    event_hash     = models.CharField(max_length=64, blank=True, db_index=True)
    # Sequence number within this evidence's chain
    sequence_number = models.PositiveIntegerField(default=0)
    # Phase 2: anchor this event hash to blockchain
    blockchain_anchored = models.BooleanField(default=False)
    blockchain_tx       = models.CharField(max_length=255, blank=True)
    metadata       = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tap_events'
        ordering = ['timestamp', 'sequence_number']

    def __str__(self):
        return f"[{self.sequence_number}] {self.event_type} on Evidence#{self.evidence_id}"

    def compute_hash(self):
        """Compute this event's chain hash.
        Incorporates previous hash to form the immutable chain.
        In Phase 2 this hash will be anchored to Ethereum/Hyperledger.
        """
        prev_hash = self.previous_event.event_hash if self.previous_event else 'GENESIS'
        raw = f"{self.event_type}{self.timestamp.isoformat()}{self.actor_id}{prev_hash}{self.evidence_id}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.event_hash:
            self.event_hash = self.compute_hash()
        super().save(*args, **kwargs)

    @property
    def color(self):
        return self.EVENT_COLORS.get(self.event_type, '#6b7280')

    @property
    def is_genesis(self):
        return self.previous_event is None

    def verify_chain_integrity(self):
        """Re-compute and compare hash — detects tampering."""
        return self.compute_hash() == self.event_hash

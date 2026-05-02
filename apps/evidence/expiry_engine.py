"""
TAP-DEV — Self-Destructing Documents Expiry Engine
Manages document expiration, IPFS unpin, blockchain state updates,
and access revocation while preserving audit trails.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class ExpiryEngine:
    """Manages document expiration lifecycle."""

    def __init__(self, evidence):
        self.evidence = evidence

    def set_expiry(self, expires_at=None, expiry_hours=None, expiry_event=None):
        """Set expiry policy on an evidence item."""
        if expiry_hours:
            self.evidence.expires_at = timezone.now() + timezone.timedelta(hours=expiry_hours)
        elif expires_at:
            self.evidence.expires_at = expires_at

        if expiry_event:
            self.evidence.expiry_condition = expiry_event

        self.evidence.expiry_enabled = True
        self.evidence.save(update_fields=['expires_at', 'expiry_enabled', 'expiry_condition'])

        # Create event chain entry
        from apps.events.engine import EventChainEngine
        engine = EventChainEngine(self.evidence)
        engine.create_event(
            'EXPIRE_SET', None,
            f'Expiry policy set: {self.evidence.expires_at.strftime("%Y-%m-%d %H:%M") if self.evidence.expires_at else "event-based"}',
            metadata={'expires_at': self.evidence.expires_at.isoformat() if self.evidence.expires_at else None}
        )

    def check_and_expire(self):
        """Check if evidence should be expired and execute if so."""
        if not self.evidence.expiry_enabled:
            return False
        if self.evidence.is_expired:
            return True  # Already expired

        now = timezone.now()
        should_expire = False

        # Time-based expiry
        if self.evidence.expires_at and now >= self.evidence.expires_at:
            should_expire = True

        if should_expire:
            self._execute_expiry()
            return True

        return False

    def _execute_expiry(self):
        """Execute the expiry: revoke access, unpin IPFS, update blockchain state."""
        self.evidence.is_expired = True
        self.evidence.expired_at = timezone.now()
        self.evidence.status = 'ARCHIVED'

        # Revoke file access (delete the actual file but keep the record)
        if self.evidence.file:
            try:
                self.evidence.file.delete(save=False)
                logger.info(f"Expired evidence #{self.evidence.pk}: file deleted")
            except Exception as e:
                logger.warning(f"Could not delete expired file: {e}")

        self.evidence.save(update_fields=[
            'is_expired', 'expired_at', 'status'
        ])

        # Unpin from IPFS (simulated)
        self._unpin_ipfs()

        # Update blockchain state
        self._update_blockchain_state()

        # Create event chain entry
        from apps.events.engine import EventChainEngine
        engine = EventChainEngine(self.evidence)
        engine.create_event(
            'EXPIRED', None,
            f'Document expired and access revoked at {self.evidence.expired_at.strftime("%Y-%m-%d %H:%M")}. '
            f'Content removed but audit trail preserved.',
            metadata={'expired_at': self.evidence.expired_at.isoformat()}
        )

        # Notify uploader
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=self.evidence.uploader,
            title='Document Expired',
            message=f'Evidence "{self.evidence.title}" has expired. '
                    f'Content access has been revoked. The audit trail remains accessible.',
            notif_type='WARNING',
            link=f'/evidence/{self.evidence.pk}/',
        )

        # Log activity
        from apps.users.utils import log_activity
        log_activity(
            self.evidence.uploader, 'EVIDENCE_EXPIRED', 'EVIDENCE',
            f'Auto-expired: {self.evidence.title}'
        )

    def _unpin_ipfs(self):
        """Unpin from IPFS (simulated or real)."""
        from apps.blockchain.models import IPFSRecord
        records = IPFSRecord.objects.filter(evidence=self.evidence, pinned=True)
        for record in records:
            record.pinned = False
            record.save(update_fields=['pinned'])
            logger.info(f"Unpinned IPFS CID {record.cid} for evidence #{self.evidence.pk}")

        # Clear CID from evidence
        if self.evidence.ipfs_cid:
            self.evidence.ipfs_cid = f"EXPIRED:{self.evidence.ipfs_cid}"
            self.evidence.save(update_fields=['ipfs_cid'])

    def _update_blockchain_state(self):
        """Record expiry state on blockchain (simulated)."""
        from apps.blockchain.models import BlockchainTransaction
        if self.evidence.blockchain_tx:
            # Create a new TX recording the expiry
            tx_hash = BlockchainTransaction.simulate_tx_hash(
                f"EXPIRED:{self.evidence.sha256_hash}"
            )
            BlockchainTransaction.objects.create(
                evidence=self.evidence,
                tx_hash=tx_hash,
                block_number=BlockchainTransaction.objects.count() + 1000,
                network='ETHEREUM_SIM',
                status='CONFIRMED',
                data_hash=f"EXPIRED:{self.evidence.sha256_hash}",
                submitter=None,
                metadata={'action': 'EXPIRE', 'original_tx': self.evidence.blockchain_tx},
            )

    def get_expiry_status(self):
        """Get the current expiry status for UI display."""
        if not self.evidence.expiry_enabled:
            return {
                'status': 'NO_EXPIRY',
                'label': 'No Expiry',
                'color': '#6b7280',
                'icon': '∞',
                'detail': 'This document has no expiry policy.',
            }

        if self.evidence.is_expired:
            return {
                'status': 'EXPIRED',
                'label': 'Expired',
                'color': '#ef4444',
                'icon': '⊘',
                'detail': f'Expired at {self.evidence.expired_at.strftime("%Y-%m-%d %H:%M") if self.evidence.expired_at else "unknown"}. Content access revoked.',
            }

        if self.evidence.expires_at:
            now = timezone.now()
            remaining = self.evidence.expires_at - now

            if remaining.total_seconds() <= 0:
                return {
                    'status': 'EXPIRING_NOW',
                    'label': 'Expiring Now',
                    'color': '#dc2626',
                    'icon': '⚠',
                    'detail': 'Document is past expiry time. Will be expired on next check.',
                }

            if remaining.days <= 1:
                hours = int(remaining.total_seconds() // 3600)
                return {
                    'status': 'EXPIRING_SOON',
                    'label': f'Expires in {hours}h',
                    'color': '#f59e0b',
                    'icon': '⏰',
                    'detail': f'Expires at {self.evidence.expires_at.strftime("%Y-%m-%d %H:%M")}',
                }

            if remaining.days <= 7:
                return {
                    'status': 'EXPIRING_WEEK',
                    'label': f'Expires in {remaining.days}d',
                    'color': '#f59e0b',
                    'icon': '⏳',
                    'detail': f'Expires at {self.evidence.expires_at.strftime("%Y-%m-%d %H:%M")}',
                }

            return {
                'status': 'ACTIVE',
                'label': f'Active ({remaining.days}d left)',
                'color': '#10b981',
                'icon': '✓',
                'detail': f'Expires at {self.evidence.expires_at.strftime("%Y-%m-%d %H:%M")}',
            }

        return {
            'status': 'EVENT_BASED',
            'label': 'Event-Based Expiry',
            'color': '#8b5cf6',
            'icon': '⚡',
            'detail': f'Expires on condition: {self.evidence.expiry_condition or "custom event"}',
        }


def process_expired_documents():
    """
    Batch job to process all expired documents.
    Should be called periodically (e.g., via Celery beat or management command).
    """
    from apps.evidence.models import Evidence

    now = timezone.now()
    candidates = Evidence.objects.filter(
        expiry_enabled=True,
        is_expired=False,
        expires_at__lte=now,
    )

    count = 0
    for evidence in candidates:
        engine = ExpiryEngine(evidence)
        if engine.check_and_expire():
            count += 1

    if count > 0:
        logger.info(f"Expired {count} documents in batch processing")

    return count

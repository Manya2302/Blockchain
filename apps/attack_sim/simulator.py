"""
TAP-DEV Phase 3 — Attack Simulator Engine
Injects synthetic attacks into evidence chains to test AI detection.
All injected events are clearly marked as SIMULATION in metadata.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

SIM_META = {'is_simulation': True, 'simulated_by': 'TAP-DEV AttackSim v3.0'}


class AttackSimulator:
    """Executes simulated attack scenarios on evidence chains."""

    def __init__(self, simulation, evidence, actor):
        self.sim = simulation
        self.evidence = evidence
        self.actor = actor
        self.log = []
        self.injected = []

    def run(self):
        """Execute the attack simulation."""
        attack_map = {
            'TIMESTAMP_TAMPER':     self._timestamp_tamper,
            'LOG_DELETION':         self._log_deletion,
            'REPLAY_ATTACK':        self._replay_attack,
            'FORGED_UPLOAD':        self._forged_upload,
            'DUPLICATE_EVENTS':     self._duplicate_events,
            'DELAYED_VERIFY':       self._delayed_verify,
            'HASH_COLLISION':       self._hash_collision,
            'PRIVILEGE_ESCALATION': self._privilege_escalation,
            'CHAIN_TRUNCATION':     self._chain_truncation,
            'METADATA_FORGE':       self._metadata_forge,
        }
        fn = attack_map.get(self.sim.attack_type)
        if fn:
            fn()
        return self.log, self.injected

    def _log_step(self, msg):
        self.log.append(f"[{timezone.now().isoformat()}] {msg}")
        logger.info(f"AttackSim #{self.sim.id}: {msg}")

    def _inject_event(self, event_type, description, timestamp=None, actor=None):
        from apps.events.models import Event
        events = list(Event.objects.filter(evidence=self.evidence).order_by('sequence_number'))
        prev = events[-1] if events else None
        seq = (prev.sequence_number + 1) if prev else 1

        e = Event(
            evidence=self.evidence,
            event_type=event_type,
            actor=actor or self.actor,
            description=f"[SIM] {description}",
            previous_event=prev,
            sequence_number=seq,
            timestamp=timestamp or timezone.now(),
            metadata={**SIM_META, 'sim_id': self.sim.id},
        )
        e.event_hash = e.compute_hash()
        e.save()
        self.injected.append(e.id)
        return e

    # ─── Attack Implementations ────────────────────────────────────

    def _timestamp_tamper(self):
        """Injects events with timestamps that go backward in time."""
        self._log_step("Initiating timestamp tampering attack...")
        events = list(self.evidence.events.order_by('-timestamp'))
        if not events:
            self._log_step("No events to tamper.")
            return

        past = events[0].timestamp - timedelta(days=5)
        e = self._inject_event('MODIFY', 'Tampered timestamp — injected in past', timestamp=past)
        self._log_step(f"Injected backward timestamp event #{e.id} at {past}")

        # Second injection even further back
        further_past = past - timedelta(hours=3)
        e2 = self._inject_event('VERIFY', 'Forged verify before actual upload', timestamp=further_past)
        self._log_step(f"Injected pre-upload verify #{e2.id}")
        self._log_step("Timestamp tampering complete. AI should detect backward timestamps.")

    def _log_deletion(self):
        """Simulates deletion by injecting a 'gap' then resuming."""
        self._log_step("Simulating log deletion attack...")
        # Jump 45 days into future (simulates missing log period)
        future = timezone.now() + timedelta(days=45)
        e = self._inject_event('NOTE', 'Resumed after log deletion gap', timestamp=future)
        self._log_step(f"Injected gap event #{e.id} — 45 day unexplained gap simulated")
        self._log_step("Log deletion simulation complete. AI should detect large gap anomaly.")

    def _replay_attack(self):
        """Injects duplicate UPLOAD events simulating replay."""
        self._log_step("Initiating replay attack...")
        for i in range(3):
            e = self._inject_event('UPLOAD', f'Replayed upload event #{i+1}')
            self._log_step(f"Injected duplicate UPLOAD #{e.id}")
        self._log_step("Replay attack complete. AI should detect multiple UPLOAD anomaly.")

    def _forged_upload(self):
        """Simulates a forged upload at beginning of chain."""
        self._log_step("Initiating forged upload injection...")
        # Inject events that violate UPLOAD-first rule
        e1 = self._inject_event('VERIFY', 'Forged verify before upload')
        e2 = self._inject_event('STORE',  'Forged store without verification')
        e3 = self._inject_event('UPLOAD', 'Late forged upload injection')
        self._log_step(f"Injected forged sequence: VERIFY→STORE→UPLOAD (events #{e1.id},{e2.id},{e3.id})")
        self._log_step("Forged upload complete. AI should detect lifecycle violation.")

    def _duplicate_events(self):
        """Injects consecutive duplicate events."""
        self._log_step("Injecting duplicate events...")
        for _ in range(4):
            e = self._inject_event('MODIFY', 'Rapid consecutive modification — automated attack')
        self._log_step(f"Injected 4 consecutive MODIFY events")
        self._log_step("Duplicate injection complete. AI should detect burst pattern.")

    def _delayed_verify(self):
        """Injects a VERIFY event 60+ days after last event."""
        self._log_step("Simulating delayed verification attack...")
        far_future = timezone.now() + timedelta(days=90)
        e = self._inject_event('VERIFY', 'Verification 90 days after last event', timestamp=far_future)
        self._log_step(f"Injected delayed verify #{e.id} — 90 day gap")
        self._log_step("Delayed verify complete. AI should detect large gap + lifecycle anomaly.")

    def _hash_collision(self):
        """Simulates hash tampering signal in chain."""
        self._log_step("Simulating hash collision / chain integrity attack...")
        # We can't actually break the chain hash (by design), but we inject
        # events that corrupt the chain and then try to repair it
        e1 = self._inject_event('MODIFY', 'Pre-tamper modification')
        # Corrupt e1's hash manually (simulation marker)
        e1.event_hash = 'aabbccdd' * 8  # Invalid hash
        e1.save(update_fields=['event_hash'])
        e2 = self._inject_event('VERIFY', 'Post-tamper verify attempt')
        self._log_step(f"Corrupted hash on event #{e1.id}")
        self._log_step("Hash collision simulation complete. AI should detect HASH_MISMATCH.")

    def _privilege_escalation(self):
        """Simulates admin-level events from a submitter context."""
        self._log_step("Simulating privilege escalation...")
        # Try to inject high-privilege operations
        e = self._inject_event('STORE', 'Unauthorized store by submitter-role actor')
        e2 = self._inject_event('FLAG',  'Unauthorized flag — escalated privileges')
        self._log_step(f"Injected privilege escalation events #{e.id}, #{e2.id}")
        self._log_step("Privilege escalation simulation complete.")

    def _chain_truncation(self):
        """Simulates detection of missing chain elements."""
        self._log_step("Simulating chain truncation attack...")
        # Skip required lifecycle steps
        e = self._inject_event('STORE', 'Store without VERIFY — chain truncated')
        self._log_step(f"Injected STORE without VERIFY #{e.id}")
        self._log_step("Chain truncation complete. AI should detect lifecycle skip.")

    def _metadata_forge(self):
        """Simulates metadata forgery via rapid note injection."""
        self._log_step("Simulating metadata forgery...")
        for i in range(5):
            e = self._inject_event('NOTE', f'Forged metadata injection #{i+1} — overwriting record')
        self._log_step("Injected 5 forged NOTE events in rapid succession")
        self._log_step("Metadata forgery complete.")

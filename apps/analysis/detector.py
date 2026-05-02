"""
TAP-DEV Anomaly Detector — Rule-Based Engine (Phase 1)

Rules:
  R1 - Chain must start with UPLOAD            → HIGH
  R2 - Invalid event transitions               → HIGH
  R3 - Backward timestamps                     → HIGH
  R4 - Large time gap (>30 days)               → LOW
  R5 - Consecutive duplicate events            → MEDIUM
  R6 - Multiple UPLOAD events                  → HIGH
  R7 - Chain hash mismatch (tampering)         → HIGH
  R8 - MODIFY after STORE                      → HIGH

Phase 3 Upgrade: Replace/augment with BiLSTM sequence anomaly detection.
"""
from datetime import timedelta
from .models import Anomaly

VALID_TRANSITIONS = {
    'UPLOAD': ['MODIFY', 'VERIFY', 'NOTE', 'FLAG', 'EXPIRE_SET'],
    'MODIFY': ['MODIFY', 'VERIFY', 'NOTE', 'FLAG', 'EXPIRE_SET'],
    'VERIFY': ['STORE', 'MODIFY', 'NOTE', 'FLAG', 'EXPIRE_SET'],
    'STORE':  ['NOTE', 'FLAG', 'EXPIRE_SET', 'EXPIRED'],
    'FLAG':   ['VERIFY', 'NOTE', 'FLAG'],
    'NOTE':   ['MODIFY', 'VERIFY', 'STORE', 'FLAG', 'NOTE', 'EXPIRE_SET'],
    'EXPIRE_SET': ['MODIFY', 'VERIFY', 'STORE', 'NOTE', 'FLAG', 'EXPIRED', 'EXPIRE_SET'],
    'EXPIRED': [],  # Terminal state
}


class AnomalyDetector:
    def __init__(self, evidence):
        self.evidence = evidence
        self.new_anomalies = []
        self.max_gap_days = 30

    def run(self):
        Anomaly.objects.filter(evidence=self.evidence, is_resolved=False).delete()
        self.new_anomalies = []

        from apps.events.models import Event
        events = list(Event.objects.filter(evidence=self.evidence).order_by('sequence_number'))
        if not events:
            return

        self._rule_upload_first(events)
        self._rule_valid_transitions(events)
        self._rule_backward_timestamps(events)
        self._rule_time_gap(events)
        self._rule_duplicate_consecutive(events)
        self._rule_multiple_uploads(events)
        self._rule_chain_integrity(events)
        Anomaly.objects.bulk_create(self.new_anomalies)

    def _flag(self, anomaly_type, description, severity, event=None):
        self.new_anomalies.append(Anomaly(
            evidence=self.evidence,
            anomaly_type=anomaly_type,
            description=description,
            severity=severity,
            related_event=event,
        ))

    def _rule_upload_first(self, events):
        if events[0].event_type != 'UPLOAD':
            self._flag('INVALID_SEQUENCE',
                f'Chain does not begin with UPLOAD. First event is {events[0].event_type}.',
                'HIGH', events[0])

    def _rule_valid_transitions(self, events):
        for i in range(1, len(events)):
            prev, curr = events[i-1].event_type, events[i].event_type
            allowed = VALID_TRANSITIONS.get(prev, [])
            if allowed and curr not in allowed:
                self._flag('INVALID_SEQUENCE',
                    f'Event #{events[i].sequence_number}: {curr} after {prev} is not a valid transition.',
                    'HIGH', events[i])
            if prev == 'STORE' and curr == 'MODIFY':
                self._flag('INVALID_SEQUENCE',
                    'MODIFY after STORE: evidence must not be modified once stored.',
                    'HIGH', events[i])

    def _rule_backward_timestamps(self, events):
        for i in range(1, len(events)):
            if events[i].timestamp < events[i-1].timestamp:
                self._flag('BACKWARD_TIMESTAMP',
                    f'Event #{events[i].sequence_number} ({events[i].event_type}) timestamp '
                    f'{events[i].timestamp} is BEFORE previous event at {events[i-1].timestamp}.',
                    'HIGH', events[i])

    def _rule_time_gap(self, events):
        for i in range(1, len(events)):
            gap = events[i].timestamp - events[i-1].timestamp
            if gap > timedelta(days=self.max_gap_days):
                self._flag('LARGE_GAP',
                    f'Event #{events[i].sequence_number}: {gap.days}-day gap since previous event.',
                    'LOW', events[i])

    def _rule_duplicate_consecutive(self, events):
        skip = {'NOTE', 'FLAG'}
        for i in range(1, len(events)):
            if events[i].event_type == events[i-1].event_type and events[i].event_type not in skip:
                self._flag('DUPLICATE_EVENT',
                    f'Consecutive duplicate: {events[i].event_type} at positions '
                    f'{events[i-1].sequence_number} and {events[i].sequence_number}.',
                    'MEDIUM', events[i])

    def _rule_multiple_uploads(self, events):
        uploads = [e for e in events if e.event_type == 'UPLOAD']
        for e in uploads[1:]:
            self._flag('INVALID_SEQUENCE',
                'Multiple UPLOAD events: only one UPLOAD is permitted per chain.',
                'HIGH', e)

    def _rule_chain_integrity(self, events):
        for event in events:
            if not event.verify_chain_integrity():
                self._flag('HASH_MISMATCH',
                    f'Chain hash mismatch at event #{event.sequence_number} — POSSIBLE TAMPERING.',
                    'HIGH', event)

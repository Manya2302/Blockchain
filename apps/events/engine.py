"""
TAP-DEV Timeline / Event Chain Engine
Manages the creation and validation of the event chain for each Evidence item.

Future Phase 2:
  - After create_event(), anchor event_hash to Ethereum via Web3.py
  - Store IPFS CID alongside event for decentralized file proof
"""
from django.utils import timezone


class EventChainEngine:
    """Manages creating chain-linked events for a given Evidence item."""

    def __init__(self, evidence):
        self.evidence = evidence

    def _event_model(self):
        from apps.events.models import Event
        return Event

    def get_latest_event(self):
        Event = self._event_model()
        return Event.objects.filter(evidence=self.evidence).order_by('-sequence_number').first()

    def get_chain(self):
        Event = self._event_model()
        return Event.objects.filter(evidence=self.evidence).order_by('sequence_number')

    def create_event(self, event_type, actor, description='', metadata=None):
        Event = self._event_model()
        tip = self.get_latest_event()
        seq = (tip.sequence_number + 1) if tip else 0
        event = Event(
            evidence=self.evidence,
            event_type=event_type,
            actor=actor,
            description=description,
            previous_event=tip,
            sequence_number=seq,
            timestamp=timezone.now(),
            metadata=metadata or {},
        )
        event.event_hash = event.compute_hash()
        event.save()
        return event

    def verify_full_chain(self):
        chain = list(self.get_chain())
        for event in chain:
            if not event.verify_chain_integrity():
                return False, event
        return True, None

    def get_timeline_data(self):
        chain  = list(self.get_chain())
        valid, broken = self.verify_full_chain()
        return {
            'events': chain,
            'chain_valid': valid,
            'broken_at': broken,
            'event_count': len(chain),
            'genesis': chain[0] if chain else None,
            'latest': chain[-1] if chain else None,
        }

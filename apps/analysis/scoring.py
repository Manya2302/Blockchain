"""
TAP-DEV Trust Scorer
Computes a 0-100 trust score based on detected anomalies.
Phase 3 upgrade: incorporate BiLSTM confidence scores into weighting.
"""
from django.conf import settings
from .models import Anomaly


class TrustScorer:
    """
    Trust Score = 100 − Σ(penalty × anomaly_count_per_severity)
    Capped at [0, 100].
    """

    def __init__(self, evidence):
        self.evidence = evidence
        self.penalties = settings.TAPDEV_CONFIG.get('TRUST_PENALTY', {'HIGH': 25, 'MEDIUM': 12, 'LOW': 5})

    def recalculate(self):
        """Recompute and persist trust_score on the Evidence record."""
        anomalies = Anomaly.objects.filter(evidence=self.evidence, is_resolved=False)
        score = 100
        for anomaly in anomalies:
            score -= self.penalties.get(anomaly.severity, 0)
        score = max(0, min(100, score))
        self.evidence.trust_score = score
        self.evidence.save(update_fields=['trust_score'])
        return score

    def get_label(self):
        s = self.evidence.trust_score
        if s >= 80: return 'Trusted'
        if s >= 50: return 'Moderate'
        if s >= 25: return 'Suspicious'
        return 'Compromised'

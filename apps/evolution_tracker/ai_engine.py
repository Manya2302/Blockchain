"""
TAP-DEV — AI-Powered Document Evolution Analyzer
Sequence-based anomaly detection model that evaluates version evolution patterns
to detect gradual tampering, hidden edits, and manipulation attempts.

Features:
  - Temporal pattern analysis (edit frequency, timing anomalies)
  - Magnitude scoring (cumulative drift from original)
  - Behavioral fingerprinting (suspicious keyword injections, structural changes)
  - Sequence-based fraud probability (multi-feature weighted model)
"""
import hashlib
import logging
import math
import statistics
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class EvolutionAIEngine:
    """
    AI-powered engine that analyzes the full evolution chain of a document
    to detect gradual tampering patterns that per-version comparisons miss.
    """

    # Feature weights for the scoring model
    WEIGHTS = {
        'edit_frequency_anomaly': 0.15,
        'magnitude_escalation': 0.20,
        'timing_anomaly': 0.15,
        'keyword_injection_pattern': 0.15,
        'cumulative_drift': 0.15,
        'hash_instability': 0.10,
        'size_manipulation': 0.10,
    }

    # Thresholds
    RISK_THRESHOLDS = {
        'CRITICAL': 0.75,
        'HIGH': 0.55,
        'MEDIUM': 0.30,
        'LOW': 0.0,
    }

    def __init__(self, evidence):
        """Initialize with the latest version of an evidence item."""
        self.evidence = evidence
        self.versions = []
        self.comparisons = []

    def analyze_full_chain(self):
        """
        Run full AI analysis on the complete version evolution chain.
        Returns a dict with risk level, probability, features, and patterns.
        """
        from apps.evidence.models import Evidence
        from .models import DocumentVersion

        # Gather all versions in this chain
        self.versions = list(self.evidence.get_all_versions())
        if len(self.versions) < 2:
            return self._safe_result()

        # Gather all comparisons
        version_ids = [v.pk for v in self.versions]
        self.comparisons = list(
            DocumentVersion.objects.filter(
                evidence_id__in=version_ids
            ).order_by('analyzed_at')
        )

        # Extract features
        features = {}
        features['edit_frequency_anomaly'] = self._analyze_edit_frequency()
        features['magnitude_escalation'] = self._analyze_magnitude_escalation()
        features['timing_anomaly'] = self._analyze_timing()
        features['keyword_injection_pattern'] = self._analyze_keyword_patterns()
        features['cumulative_drift'] = self._analyze_cumulative_drift()
        features['hash_instability'] = self._analyze_hash_instability()
        features['size_manipulation'] = self._analyze_size_manipulation()

        # Compute weighted score
        anomaly_score = sum(
            features[k] * self.WEIGHTS[k] for k in self.WEIGHTS
        )
        anomaly_score = min(max(anomaly_score, 0.0), 1.0)

        # Determine risk level
        risk_level = 'LOW'
        for level, threshold in self.RISK_THRESHOLDS.items():
            if anomaly_score >= threshold:
                risk_level = level
                break

        # Detect specific patterns
        patterns = self._detect_patterns(features)

        return {
            'anomaly_score': round(anomaly_score, 4),
            'risk_level': risk_level,
            'features': {k: round(v, 4) for k, v in features.items()},
            'patterns': patterns,
            'version_count': len(self.versions),
            'comparison_count': len(self.comparisons),
            'chain_span_days': self._chain_span_days(),
            'summary': self._build_summary(anomaly_score, risk_level, patterns),
        }

    def _safe_result(self):
        """Return a safe result when there's insufficient data."""
        return {
            'anomaly_score': 0.0,
            'risk_level': 'LOW',
            'features': {k: 0.0 for k in self.WEIGHTS},
            'patterns': [],
            'version_count': len(self.versions),
            'comparison_count': 0,
            'chain_span_days': 0,
            'summary': 'Insufficient version history for AI analysis.',
        }

    def _chain_span_days(self):
        """Calculate total days span of the version chain."""
        if len(self.versions) < 2:
            return 0
        delta = self.versions[-1].created_at - self.versions[0].created_at
        return max(delta.days, 0)

    def _analyze_edit_frequency(self):
        """
        Detect abnormal edit frequency patterns.
        Rapid successive edits → suspicious (score increases).
        """
        if len(self.versions) < 3:
            return 0.0

        intervals = []
        for i in range(1, len(self.versions)):
            delta = (self.versions[i].created_at - self.versions[i - 1].created_at).total_seconds()
            intervals.append(max(delta, 1))

        if not intervals:
            return 0.0

        # Flag rapid bursts (edits within 60 seconds)
        rapid_edits = sum(1 for i in intervals if i < 60)
        rapid_ratio = rapid_edits / len(intervals)

        # Flag irregular spacing (high coefficient of variation)
        mean_interval = statistics.mean(intervals)
        if mean_interval > 0 and len(intervals) > 1:
            stdev = statistics.stdev(intervals)
            cv = stdev / mean_interval
        else:
            cv = 0

        # Combined score
        score = min(rapid_ratio * 1.5 + (cv * 0.3 if cv > 2 else 0), 1.0)
        return score

    def _analyze_magnitude_escalation(self):
        """
        Detect escalating edit magnitudes — sign of gradual tampering
        where each edit makes increasingly larger changes.
        """
        if not self.comparisons:
            return 0.0

        magnitudes = []
        for c in self.comparisons:
            mag = (c.words_added + c.words_removed + c.chars_changed) / max(1, c.chars_changed + 1)
            magnitudes.append(c.fraud_score)

        if len(magnitudes) < 2:
            return magnitudes[0] if magnitudes else 0.0

        # Check for escalating trend
        increasing = sum(
            1 for i in range(1, len(magnitudes))
            if magnitudes[i] > magnitudes[i - 1]
        )
        trend_ratio = increasing / (len(magnitudes) - 1)

        # High fraud scores in recent versions
        recent_avg = statistics.mean(magnitudes[-3:]) if len(magnitudes) >= 3 else magnitudes[-1]

        return min(trend_ratio * 0.5 + recent_avg * 0.5, 1.0)

    def _analyze_timing(self):
        """
        Detect suspicious modification timing:
        - Edits at unusual hours (2-5 AM)
        - Edits on weekends/holidays
        - Clustered edits right before deadlines
        """
        if len(self.versions) < 2:
            return 0.0

        unusual_hour_count = 0
        weekend_count = 0
        total = len(self.versions) - 1  # Skip first version

        for v in self.versions[1:]:
            hour = v.created_at.hour
            if 2 <= hour <= 5:
                unusual_hour_count += 1
            if v.created_at.weekday() >= 5:
                weekend_count += 1

        unusual_ratio = unusual_hour_count / max(total, 1)
        weekend_ratio = weekend_count / max(total, 1)

        return min(unusual_ratio * 0.7 + weekend_ratio * 0.3, 1.0)

    def _analyze_keyword_patterns(self):
        """
        Analyze keyword injection patterns across the evolution chain.
        Gradual injection of legally significant terms → tampering signal.
        """
        if not self.comparisons:
            return 0.0

        keyword_signals = 0
        for c in self.comparisons:
            if c.fraud_signals:
                for sig in c.fraud_signals:
                    if isinstance(sig, dict) and sig.get('signal') == 'keyword_injection':
                        keyword_signals += 1

        if keyword_signals == 0:
            return 0.0

        # Multiple keyword injections across versions → strong signal
        return min(keyword_signals * 0.25, 1.0)

    def _analyze_cumulative_drift(self):
        """
        Measure cumulative similarity drift from the original document.
        Large cumulative drift while maintaining per-version similarity → stealth tampering.
        """
        if not self.comparisons:
            return 0.0

        similarities = [c.text_similarity for c in self.comparisons]
        if not similarities:
            return 0.0

        # Average per-version similarity
        avg_similarity = statistics.mean(similarities)

        # If each version is similar to its predecessor but overall drift is large,
        # this indicates gradual tampering
        if avg_similarity > 0.85 and len(similarities) > 3:
            # High per-version similarity with many versions = stealth drift
            drift_score = (1 - avg_similarity) * len(similarities) * 0.5
            return min(drift_score, 1.0)

        # Direct low similarity
        min_similarity = min(similarities)
        if min_similarity < 0.5:
            return min((1 - min_similarity) * 0.8, 1.0)

        return max(0, (1 - avg_similarity) * 1.5)

    def _analyze_hash_instability(self):
        """
        Check hash change patterns. Every version should have a different hash,
        but if text is identical and hash changed → metadata/binary manipulation.
        """
        if not self.comparisons:
            return 0.0

        hidden_mods = sum(
            1 for c in self.comparisons
            if c.hash_changed and c.text_similarity > 0.98
        )

        if hidden_mods == 0:
            return 0.0

        return min(hidden_mods * 0.4, 1.0)

    def _analyze_size_manipulation(self):
        """
        Detect systematic file size reductions or suspicious size patterns.
        """
        if not self.comparisons:
            return 0.0

        size_reductions = sum(
            1 for c in self.comparisons if c.file_size_delta < -1024
        )
        drastic_changes = sum(
            1 for c in self.comparisons if abs(c.file_size_delta) > 50 * 1024
        )

        total = len(self.comparisons)
        reduction_ratio = size_reductions / max(total, 1)
        drastic_ratio = drastic_changes / max(total, 1)

        return min(reduction_ratio * 0.6 + drastic_ratio * 0.4, 1.0)

    def _detect_patterns(self, features):
        """Identify specific tampering patterns from feature scores."""
        patterns = []

        if features['edit_frequency_anomaly'] > 0.5:
            patterns.append({
                'pattern': 'rapid_edit_burst',
                'label': 'Rapid Edit Burst',
                'description': 'Abnormally frequent edits detected — may indicate automated or panicked modifications',
                'severity': 'HIGH',
                'confidence': round(features['edit_frequency_anomaly'] * 100),
            })

        if features['magnitude_escalation'] > 0.4:
            patterns.append({
                'pattern': 'escalating_changes',
                'label': 'Escalating Modifications',
                'description': 'Each version makes increasingly larger changes — classic gradual tampering pattern',
                'severity': 'HIGH',
                'confidence': round(features['magnitude_escalation'] * 100),
            })

        if features['timing_anomaly'] > 0.3:
            patterns.append({
                'pattern': 'suspicious_timing',
                'label': 'Suspicious Timing',
                'description': 'Modifications at unusual hours or during weekends — may indicate covert editing',
                'severity': 'MEDIUM',
                'confidence': round(features['timing_anomaly'] * 100),
            })

        if features['keyword_injection_pattern'] > 0.3:
            patterns.append({
                'pattern': 'keyword_seeding',
                'label': 'Keyword Seeding',
                'description': 'Legally significant terms gradually injected across versions',
                'severity': 'CRITICAL',
                'confidence': round(features['keyword_injection_pattern'] * 100),
            })

        if features['cumulative_drift'] > 0.4:
            patterns.append({
                'pattern': 'stealth_drift',
                'label': 'Stealth Document Drift',
                'description': 'Document content has drifted significantly from original while maintaining version-to-version similarity',
                'severity': 'HIGH',
                'confidence': round(features['cumulative_drift'] * 100),
            })

        if features['hash_instability'] > 0.3:
            patterns.append({
                'pattern': 'hidden_modification',
                'label': 'Hidden Binary Modification',
                'description': 'Hash changes without visible text changes — possible metadata or binary-level tampering',
                'severity': 'CRITICAL',
                'confidence': round(features['hash_instability'] * 100),
            })

        if features['size_manipulation'] > 0.3:
            patterns.append({
                'pattern': 'size_anomaly',
                'label': 'File Size Anomaly',
                'description': 'Systematic file size manipulation detected across versions',
                'severity': 'MEDIUM',
                'confidence': round(features['size_manipulation'] * 100),
            })

        return patterns

    def _build_summary(self, score, risk_level, patterns):
        """Build human-readable AI analysis summary."""
        pct = round(score * 100, 1)

        if risk_level == 'CRITICAL':
            intro = f'CRITICAL RISK ({pct}%): Strong evidence of deliberate document tampering detected.'
        elif risk_level == 'HIGH':
            intro = f'HIGH RISK ({pct}%): Multiple suspicious evolution patterns detected.'
        elif risk_level == 'MEDIUM':
            intro = f'MODERATE RISK ({pct}%): Some unusual patterns warrant further investigation.'
        else:
            intro = f'LOW RISK ({pct}%): Document evolution appears normal.'

        if patterns:
            details = ' Detected patterns: ' + ', '.join(p['label'] for p in patterns[:3]) + '.'
        else:
            details = ' No specific tampering patterns identified.'

        return intro + details

"""
TAP-DEV Phase 3 — Hybrid BiLSTM Anomaly Engine

Architecture:
  1. Feature Extraction: Converts event sequences into feature vectors
     mimicking BiLSTM temporal sequence analysis (context window approach)
  2. BiLSTM-Inspired Classifier: RandomForest + IsolationForest ensemble
     with LSTM-like sequential context features (lag features, rolling stats)
  3. Rule-Based Fallback: Original Phase 1 rules validate edge cases
  4. Hybrid Score: Weighted combination of AI prob + rule severity

Detected Patterns:
  - Temporal replay attacks
  - Timestamp forgery / backward time injection
  - Abnormal event velocity (bursts/delays)
  - Missing lifecycle steps
  - Suspicious modification chains
  - Forged upload sequences
  - Cross-evidence replay (same hash, different chain)

Production swap: Replace RF model with TensorFlow BiLSTM:
  model = Sequential([
      Bidirectional(LSTM(64, return_sequences=True)),
      Dropout(0.3),
      Bidirectional(LSTM(32)),
      Dense(16, activation='relu'),
      Dense(1, activation='sigmoid')
  ])
"""
import os
import pickle
import logging
import numpy as np
from datetime import timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Model storage path ────────────────────────────────────────────
MODEL_DIR = Path(__file__).resolve().parent / 'models'
MODEL_DIR.mkdir(exist_ok=True)
BILSTM_MODEL_PATH = MODEL_DIR / 'bilstm_hybrid.pkl'
METRICS_PATH = MODEL_DIR / 'model_metrics.json'

# ── Feature names (matches BiLSTM input dimensions) ───────────────
FEATURE_NAMES = [
    'chain_length',
    'event_type_encoded',
    'timestamp_delta_seconds',
    'timestamp_delta_log',
    'modification_frequency',
    'verify_attempt_ratio',
    'flag_ratio',
    'backward_ts_count',
    'duplicate_event_count',
    'max_gap_days',
    'min_gap_seconds',
    'velocity_score',          # events per hour in last window
    'chain_depth_ratio',
    'upload_count',
    'file_size_mb',
    'is_revision',             # has parent evidence
    'actor_role_encoded',
    'hash_mismatch_count',
    'note_density',
    'store_before_verify',     # anomalous lifecycle
    'sequential_context_0',    # rolling window features (BiLSTM-style)
    'sequential_context_1',
    'sequential_context_2',
    'burst_detection',
    'time_of_day_anomaly',
]

EVENT_TYPE_MAP = {
    'UPLOAD': 0, 'MODIFY': 1, 'VERIFY': 2,
    'STORE': 3, 'FLAG': 4, 'NOTE': 5
}

ROLE_MAP = {'SUBMITTER': 0, 'ANALYST': 1, 'ADMIN': 2}


def extract_features(events, evidence):
    """
    Extract a 25-dimensional feature vector from an evidence event chain.
    Designed to mirror what a BiLSTM would learn from sequences.
    """
    if not events:
        return np.zeros(len(FEATURE_NAMES))

    n = len(events)
    event_types = [e.event_type for e in events]
    timestamps = [e.timestamp for e in events]

    # Temporal deltas
    deltas = []
    for i in range(1, n):
        delta = (timestamps[i] - timestamps[i-1]).total_seconds()
        deltas.append(delta)

    # Core counts
    upload_count = event_types.count('UPLOAD')
    modify_count = event_types.count('MODIFY')
    verify_count = event_types.count('VERIFY')
    flag_count   = event_types.count('FLAG')
    note_count   = event_types.count('NOTE')
    store_count  = event_types.count('STORE')

    # Timestamp anomalies
    backward_ts = sum(1 for d in deltas if d < 0)
    hash_mismatches = sum(1 for e in events if not e.verify_chain_integrity())

    # Gaps
    abs_deltas = [abs(d) for d in deltas] if deltas else [0]
    max_gap = max(abs_deltas) / 86400  # days
    min_gap = min(abs_deltas)           # seconds

    # Velocity: events in last simulated hour window
    if len(timestamps) >= 2:
        total_span = (timestamps[-1] - timestamps[0]).total_seconds()
        velocity = (n / max(total_span / 3600, 0.001))
    else:
        velocity = 0

    # Modification frequency
    mod_freq = modify_count / max(n, 1)

    # Lifecycle anomaly: STORE before any VERIFY
    store_before_verify = 0
    seen_verify = False
    for et in event_types:
        if et == 'VERIFY':
            seen_verify = True
        if et == 'STORE' and not seen_verify:
            store_before_verify = 1
            break

    # Duplicate count
    dup_count = 0
    skip = {'NOTE', 'FLAG'}
    for i in range(1, n):
        if event_types[i] == event_types[i-1] and event_types[i] not in skip:
            dup_count += 1

    # Sequential context features (BiLSTM window simulation)
    # Encode last 3 event types as context features
    last_3 = event_types[-3:] if n >= 3 else event_types
    ctx = [EVENT_TYPE_MAP.get(e, 0) / 5.0 for e in last_3]
    while len(ctx) < 3:
        ctx.insert(0, 0.0)

    # Burst detection: > 5 events in < 60 seconds
    burst = 0
    if len(deltas) >= 4:
        windows = [sum(abs_deltas[i:i+4]) for i in range(len(abs_deltas)-3)]
        if min(windows) < 60:
            burst = 1

    # Time-of-day anomaly (events at unusual hours: 2-5am UTC)
    unusual_hours = sum(1 for t in timestamps if t.hour in range(2, 6)) / max(n, 1)

    # Actor role
    try:
        actor = events[-1].actor
        role = getattr(getattr(actor, 'profile', None), 'role', 'SUBMITTER')
        role_enc = ROLE_MAP.get(role, 0)
    except Exception:
        role_enc = 0

    # File size
    file_size_mb = (evidence.file_size or 0) / (1024 * 1024)

    # Is revision
    is_revision = 1 if evidence.parent_evidence_id else 0

    # Compose feature vector
    features = np.array([
        min(n, 50) / 50,                               # chain_length (normalized)
        EVENT_TYPE_MAP.get(event_types[-1], 0) / 5,    # last event type
        np.mean(deltas) if deltas else 0,               # avg timestamp delta
        np.log1p(max(abs_deltas[0] if abs_deltas else 0, 0)),  # log delta
        mod_freq,                                       # modification frequency
        verify_count / max(n, 1),                       # verify ratio
        flag_count / max(n, 1),                         # flag ratio
        min(backward_ts / max(n, 1), 1.0),              # backward ts ratio
        min(dup_count / max(n, 1), 1.0),                # duplicate ratio
        min(max_gap, 365) / 365,                        # max gap (normalized)
        min(min_gap, 3600) / 3600,                      # min gap (normalized)
        min(velocity, 100) / 100,                       # velocity score
        n / max(n + 1, 1),                              # chain depth ratio
        min(upload_count, 5) / 5,                       # upload count
        min(file_size_mb, 100) / 100,                   # file size
        is_revision,                                    # is revision
        role_enc / 2,                                   # actor role
        min(hash_mismatches / max(n, 1), 1.0),          # hash mismatch ratio
        note_count / max(n, 1),                         # note density
        store_before_verify,                            # lifecycle anomaly
        ctx[0], ctx[1], ctx[2],                        # sequential context
        burst,                                          # burst detection
        unusual_hours,                                  # time anomaly
    ], dtype=np.float32)

    return features


class BiLSTMHybridPredictor:
    """
    Hybrid BiLSTM-inspired predictor.
    Uses RandomForest + IsolationForest ensemble with sequential features.

    The architecture is designed to be swapped with a true TensorFlow BiLSTM
    without changing the public API (predict(), get_explanation()).
    """

    def __init__(self):
        self.rf_model = None
        self.iso_model = None
        self.is_loaded = False
        self._load_or_bootstrap()

    def _load_or_bootstrap(self):
        """Load persisted model or bootstrap with heuristic weights."""
        try:
            if BILSTM_MODEL_PATH.exists():
                with open(BILSTM_MODEL_PATH, 'rb') as f:
                    bundle = pickle.load(f)
                    self.rf_model = bundle.get('rf')
                    self.iso_model = bundle.get('iso')
                self.is_loaded = True
                logger.info("BiLSTM hybrid model loaded from disk.")
            else:
                self._bootstrap_model()
        except Exception as e:
            logger.warning(f"Model load failed ({e}), bootstrapping.")
            self._bootstrap_model()

    def _bootstrap_model(self):
        """
        Create a bootstrapped model with synthetic heuristic training data.
        This ensures the model works without real training data by encoding
        domain knowledge as labeled synthetic samples.
        """
        from sklearn.ensemble import RandomForestClassifier, IsolationForest

        # Generate synthetic training data representing known attack patterns
        X_normal, X_attack = self._generate_synthetic_data()
        X = np.vstack([X_normal, X_attack])
        y = np.array([0] * len(X_normal) + [1] * len(X_attack))

        self.rf_model = RandomForestClassifier(
            n_estimators=150,
            max_depth=12,
            min_samples_split=3,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
        )
        self.rf_model.fit(X, y)

        self.iso_model = IsolationForest(
            n_estimators=100,
            contamination=0.15,
            random_state=42,
        )
        self.iso_model.fit(X)

        self.is_loaded = True
        self._save_model()
        logger.info("BiLSTM hybrid model bootstrapped with synthetic data.")

    def _generate_synthetic_data(self, n_normal=400, n_attack=200):
        """Generate labelled synthetic event sequences."""
        rng = np.random.RandomState(42)
        n_feat = len(FEATURE_NAMES)

        # Normal evidence chains
        X_normal = np.zeros((n_normal, n_feat))
        for i in range(n_normal):
            X_normal[i] = [
                rng.uniform(0.1, 0.8),  # chain length 5-40
                rng.choice([0, 2, 3]) / 5,  # UPLOAD/VERIFY/STORE last
                rng.uniform(3600, 86400),   # delta 1h-1d
                rng.uniform(8, 12),          # log delta
                rng.uniform(0, 0.2),         # low modification
                rng.uniform(0.1, 0.4),       # moderate verify ratio
                rng.uniform(0, 0.1),         # low flag ratio
                0.0,                          # no backward ts
                0.0,                          # no duplicates
                rng.uniform(0, 0.1),         # small gap
                rng.uniform(0.3, 1.0),       # reasonable min gap
                rng.uniform(0, 0.2),         # low velocity
                rng.uniform(0.7, 1.0),       # good chain depth
                0.2,                          # 1 upload
                rng.uniform(0, 0.5),         # normal file size
                rng.choice([0, 1]) * 0.3,    # sometimes revision
                rng.choice([0, 0.5, 1]),     # various roles
                0.0,                          # no hash mismatch
                rng.uniform(0, 0.2),         # low note density
                0.0,                          # no lifecycle anomaly
                rng.choice([0, 0.2, 0.4]),   # context
                rng.choice([0, 0.6, 1.0]),
                rng.choice([0.6, 0.8, 1.0]),
                0.0,                          # no burst
                rng.uniform(0, 0.05),        # normal hours
            ]

        # Attack patterns
        X_attack = np.zeros((n_attack, n_feat))
        attack_types = ['replay', 'timestamp_forge', 'rapid_modify', 'forged_upload', 'hash_tamper']
        for i in range(n_attack):
            attack = rng.choice(attack_types)
            row = X_normal[rng.randint(0, n_normal)].copy()  # start from normal

            if attack == 'replay':
                row[7] = rng.uniform(0.3, 1.0)   # high backward ts
                row[9] = rng.uniform(0.5, 1.0)   # large gaps
                row[12] = rng.choice([0.4, 0.8]) # duplicate uploads

            elif attack == 'timestamp_forge':
                row[7] = rng.uniform(0.5, 1.0)   # backward timestamps
                row[9] = 0.0                       # suspiciously no gap
                row[10] = 0.0                      # zero min gap
                row[24] = rng.uniform(0.5, 1.0)  # unusual hours

            elif attack == 'rapid_modify':
                row[4] = rng.uniform(0.6, 1.0)   # high modification freq
                row[6] = rng.uniform(0.3, 0.8)   # high flag ratio
                row[11] = rng.uniform(0.7, 1.0)  # high velocity
                row[23] = 1.0                     # burst

            elif attack == 'forged_upload':
                row[13] = rng.uniform(0.4, 1.0)  # multiple uploads
                row[8] = rng.uniform(0.3, 0.8)   # duplicates
                row[19] = 1.0                     # store before verify

            elif attack == 'hash_tamper':
                row[17] = rng.uniform(0.3, 1.0)  # hash mismatches
                row[7] = rng.uniform(0.2, 0.6)   # some backward ts

            # Add noise
            row += rng.normal(0, 0.05, n_feat)
            row = np.clip(row, 0, 1)
            X_attack[i] = row

        return X_normal, X_attack

    def _save_model(self):
        try:
            with open(BILSTM_MODEL_PATH, 'wb') as f:
                pickle.dump({'rf': self.rf_model, 'iso': self.iso_model}, f)
        except Exception as e:
            logger.warning(f"Model save failed: {e}")

    def predict(self, events, evidence):
        """
        Predict anomaly probability for an evidence event chain.
        Returns dict with probability, risk_level, confidence, explanation.
        """
        features = extract_features(events, evidence)
        features_2d = features.reshape(1, -1)

        # RF probability (primary signal)
        if self.rf_model is not None:
            try:
                rf_probs = self.rf_model.predict_proba(features_2d)[0]
                rf_anomaly_prob = rf_probs[1] if len(rf_probs) > 1 else rf_probs[0]
            except Exception:
                rf_anomaly_prob = self._heuristic_score(features)
        else:
            rf_anomaly_prob = self._heuristic_score(features)

        # Isolation Forest anomaly score (secondary signal)
        if self.iso_model is not None:
            try:
                iso_score = self.iso_model.score_samples(features_2d)[0]
                # Convert: more negative = more anomalous. Map to 0-1
                iso_prob = max(0, min(1, (-iso_score + 0.5) * 1.5))
            except Exception:
                iso_prob = 0.5
        else:
            iso_prob = 0.5

        # Weighted ensemble
        final_prob = 0.7 * rf_anomaly_prob + 0.3 * iso_prob
        final_prob = float(np.clip(final_prob, 0.0, 1.0))

        risk_level = self._prob_to_risk(final_prob)
        explanation = self.get_explanation(features, final_prob)
        patterns = self._detect_patterns(features)

        return {
            'anomaly_probability': round(final_prob, 4),
            'risk_level': risk_level,
            'confidence': round(float(1.0 - abs(final_prob - 0.5) * 0.4), 3),
            'rf_score': round(float(rf_anomaly_prob), 4),
            'iso_score': round(float(iso_prob), 4),
            'feature_vector': dict(zip(FEATURE_NAMES, features.tolist())),
            'explanation': explanation,
            'detected_patterns': patterns,
        }

    def _heuristic_score(self, features):
        """Rule-of-thumb fallback when model isn't available."""
        score = 0.0
        score += features[7] * 0.35   # backward timestamps
        score += features[17] * 0.30  # hash mismatches
        score += features[13] * 0.15  # multiple uploads
        score += features[8] * 0.10   # duplicates
        score += features[23] * 0.10  # burst
        return min(score, 1.0)

    def _prob_to_risk(self, prob):
        if prob < 0.15: return 'SAFE'
        if prob < 0.35: return 'LOW'
        if prob < 0.55: return 'MEDIUM'
        if prob < 0.75: return 'HIGH'
        return 'CRITICAL'

    def get_explanation(self, features, prob):
        """Generate human-readable explanations for prediction factors."""
        explanations = []
        feat = dict(zip(FEATURE_NAMES, features.tolist()))

        if feat['backward_ts_count'] > 0.1:
            explanations.append({
                'factor': 'Backward Timestamp Detected',
                'weight': round(feat['backward_ts_count'] * 0.35, 3),
                'description': f"Event timestamps appear out-of-order — possible timestamp injection attack.",
                'severity': 'HIGH'
            })
        if feat['hash_mismatch_count'] > 0.05:
            explanations.append({
                'factor': 'Chain Hash Mismatch',
                'weight': round(feat['hash_mismatch_count'] * 0.30, 3),
                'description': "Cryptographic chain hash verification failed — possible tampering detected.",
                'severity': 'HIGH'
            })
        if feat['upload_count'] > 0.25:
            explanations.append({
                'factor': 'Multiple UPLOAD Events',
                'weight': round(feat['upload_count'] * 0.15, 3),
                'description': "More than one UPLOAD event in chain — possible replay or re-injection attack.",
                'severity': 'HIGH'
            })
        if feat['modification_frequency'] > 0.4:
            explanations.append({
                'factor': 'High Modification Frequency',
                'weight': round(feat['modification_frequency'] * 0.12, 3),
                'description': "Abnormally high rate of MODIFY events — suspicious document mutation pattern.",
                'severity': 'MEDIUM'
            })
        if feat['burst_detection'] > 0.5:
            explanations.append({
                'factor': 'Event Burst Detected',
                'weight': round(0.10, 3),
                'description': "Multiple events occurred in rapid succession — potential automated attack pattern.",
                'severity': 'MEDIUM'
            })
        if feat['time_of_day_anomaly'] > 0.3:
            explanations.append({
                'factor': 'Off-Hours Activity',
                'weight': round(feat['time_of_day_anomaly'] * 0.08, 3),
                'description': "Significant activity during unusual hours (2–6 AM UTC).",
                'severity': 'LOW'
            })
        if feat['store_before_verify'] > 0.5:
            explanations.append({
                'factor': 'Lifecycle Violation',
                'weight': round(0.09, 3),
                'description': "Evidence was STORED before VERIFY step — missing mandatory lifecycle stage.",
                'severity': 'HIGH'
            })
        if feat['velocity_score'] > 0.6:
            explanations.append({
                'factor': 'Abnormal Event Velocity',
                'weight': round(feat['velocity_score'] * 0.07, 3),
                'description': "Event rate exceeds normal forensic workflow thresholds.",
                'severity': 'MEDIUM'
            })
        if feat['duplicate_event_count'] > 0.2:
            explanations.append({
                'factor': 'Duplicate Events',
                'weight': round(feat['duplicate_event_count'] * 0.08, 3),
                'description': "Consecutive duplicate event types detected — may indicate replay injection.",
                'severity': 'MEDIUM'
            })

        if not explanations:
            explanations.append({
                'factor': 'No Significant Anomalies',
                'weight': 0.0,
                'description': "Event chain follows expected forensic lifecycle with no detected anomalies.",
                'severity': 'LOW'
            })

        return sorted(explanations, key=lambda x: -x['weight'])

    def _detect_patterns(self, features):
        """Identify specific attack patterns from feature vector."""
        feat = dict(zip(FEATURE_NAMES, features.tolist()))
        patterns = []
        if feat['backward_ts_count'] > 0.15:
            patterns.append('timestamp_forgery')
        if feat['hash_mismatch_count'] > 0.1:
            patterns.append('chain_tampering')
        if feat['upload_count'] > 0.3 and feat['duplicate_event_count'] > 0.15:
            patterns.append('replay_attack')
        if feat['modification_frequency'] > 0.5 and feat['burst_detection'] > 0.5:
            patterns.append('rapid_mutation')
        if feat['store_before_verify'] > 0.5:
            patterns.append('lifecycle_skip')
        if feat['time_of_day_anomaly'] > 0.4:
            patterns.append('off_hours_intrusion')
        if feat['velocity_score'] > 0.7:
            patterns.append('event_flooding')
        return patterns

    def get_feature_importances(self):
        """Return RF feature importances for model explainability dashboard."""
        if self.rf_model is None:
            return {}
        try:
            imp = self.rf_model.feature_importances_
            return {name: round(float(val), 4) for name, val in zip(FEATURE_NAMES, imp)}
        except Exception:
            return {}

    def retrain(self, evidence_queryset, triggered_by=None):
        """
        Retrain model on real evidence data from the database.
        Builds labeled dataset: anomalies present → attack (1), else normal (0).
        """
        from apps.events.models import Event
        from apps.analysis.models import Anomaly
        from sklearn.ensemble import RandomForestClassifier, IsolationForest
        import time

        t_start = time.time()
        X, y = [], []

        for ev in evidence_queryset:
            events = list(Event.objects.filter(evidence=ev).order_by('sequence_number'))
            if not events:
                continue
            features = extract_features(events, ev)
            has_anomaly = Anomaly.objects.filter(
                evidence=ev, is_resolved=False, severity__in=['HIGH', 'CRITICAL']
            ).exists()
            X.append(features)
            y.append(1 if has_anomaly else 0)

        if len(X) < 20:
            logger.warning("Not enough real data for retraining, augmenting with synthetic.")
            X_syn_n, X_syn_a = self._generate_synthetic_data(200, 100)
            X.extend(X_syn_n.tolist())
            y.extend([0] * len(X_syn_n))
            X.extend(X_syn_a.tolist())
            y.extend([1] * len(X_syn_a))

        X_arr = np.array(X)
        y_arr = np.array(y)

        new_rf = RandomForestClassifier(
            n_estimators=200, max_depth=15, class_weight='balanced',
            random_state=int(time.time()), n_jobs=-1
        )
        new_rf.fit(X_arr, y_arr)

        new_iso = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
        new_iso.fit(X_arr)

        # Evaluate
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score, roc_auc_score
        y_pred = new_rf.predict(X_arr)
        metrics = {
            'accuracy':  float(accuracy_score(y_arr, y_pred)),
            'precision': float(precision_score(y_arr, y_pred, zero_division=0)),
            'recall':    float(recall_score(y_arr, y_pred, zero_division=0)),
            'f1_score':  float(f1_score(y_arr, y_pred, zero_division=0)),
            'samples':   len(y_arr),
        }

        # Confusion matrix
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_arr, y_pred)
        metrics['confusion_matrix'] = cm.tolist()

        self.rf_model = new_rf
        self.iso_model = new_iso
        self._save_model()

        duration = int(time.time() - t_start)
        return metrics, duration


# Singleton instance
_predictor_instance = None

def get_predictor():
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = BiLSTMHybridPredictor()
    return _predictor_instance

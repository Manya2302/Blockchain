"""TAP-DEV Phase 5 — Quantum-Resistant Cryptography"""
import uuid, hashlib, secrets
from django.db import models
from django.contrib.auth.models import User


class QuantumSignature(models.Model):
    ALGORITHM = [("CRYSTALS_DILITHIUM","CRYSTALS-Dilithium"),("CRYSTALS_KYBER","CRYSTALS-Kyber"),
                 ("FALCON","FALCON"),("SPHINCS","SPHINCS+"),("XMSS","XMSS"),("PICNIC","Picnic")]
    SECURITY_LEVEL = [(1,"NIST Level 1 (128-bit)"),(2,"NIST Level 2"),(3,"NIST Level 3 (192-bit)"),(5,"NIST Level 5 (256-bit)")]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evidence        = models.ForeignKey("tap_evidence.Evidence", on_delete=models.CASCADE, related_name="quantum_sigs")
    algorithm       = models.CharField(max_length=30, choices=ALGORITHM, default="CRYSTALS_DILITHIUM")
    security_level  = models.IntegerField(choices=SECURITY_LEVEL, default=3)
    public_key_hash = models.CharField(max_length=64)
    signature_hash  = models.CharField(max_length=64)
    lattice_params  = models.JSONField(default=dict)
    created_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    is_valid        = models.BooleanField(default=True)
    quantum_threat_resistant = models.BooleanField(default=True)

    class Meta:
        db_table = "tap_quantum_sigs"
        ordering = ["-created_at"]

    def __str__(self): return f"{self.algorithm} sig for Evidence#{self.evidence_id}"

    @staticmethod
    def generate_pq_keypair(algorithm="CRYSTALS_DILITHIUM"):
        """Simulate post-quantum key generation (Dilithium lattice parameters)."""
        seed = secrets.token_bytes(32)
        pk = hashlib.shake_256(seed + b"pk").hexdigest(64)
        sk_hash = hashlib.shake_256(seed + b"sk").hexdigest(32)
        params = {"algorithm": algorithm, "n": 256, "q": 8380417,
                  "tau": 49, "eta": 4, "security_level": "NIST-3"}
        return pk, sk_hash, params

    @staticmethod
    def sign_evidence(evidence_hash, sk_hash, algorithm="CRYSTALS_DILITHIUM"):
        """Simulate post-quantum signing."""
        sig = hashlib.shake_256(f"{evidence_hash}{sk_hash}{algorithm}".encode()).hexdigest(64)
        return sig

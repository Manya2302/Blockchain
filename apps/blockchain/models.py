"""
TAP-DEV Phase 2 — Blockchain Simulation Models
Simulates Ethereum/Hyperledger transaction anchoring.
Phase 3: Replace with real Web3.py + Solidity contract calls.
"""
import hashlib, time
from django.db import models


class BlockchainTransaction(models.Model):
    NETWORK_CHOICES = [
        ('ETHEREUM_SIM','Ethereum (Simulation)'),
        ('HYPERLEDGER_SIM','Hyperledger (Simulation)'),
        ('ETHEREUM','Ethereum Mainnet'),
        ('POLYGON','Polygon'),
    ]
    STATUS_CHOICES = [('PENDING','Pending'),('CONFIRMED','Confirmed'),('FAILED','Failed')]

    evidence      = models.ForeignKey('tap_evidence.Evidence', on_delete=models.CASCADE, related_name='blockchain_txs')
    event         = models.ForeignKey('tap_events.Event', null=True, blank=True, on_delete=models.SET_NULL)
    tx_hash       = models.CharField(max_length=66, unique=True)
    block_number  = models.BigIntegerField(default=0)
    network       = models.CharField(max_length=30, choices=NETWORK_CHOICES, default='ETHEREUM_SIM')
    status        = models.CharField(max_length=15, choices=STATUS_CHOICES, default='CONFIRMED')
    gas_used      = models.BigIntegerField(default=0)
    data_hash     = models.CharField(max_length=64)
    submitter     = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    anchored_at   = models.DateTimeField(auto_now_add=True)
    metadata      = models.JSONField(default=dict)

    class Meta:
        db_table = 'tap_blockchain_txs'
        ordering = ['-anchored_at']

    def __str__(self): return f"{self.tx_hash[:16]}… [{self.network}]"

    @staticmethod
    def simulate_tx_hash(data_hash, timestamp=None):
        ts = timestamp or time.time()
        raw = f"{data_hash}{ts}{time.time_ns()}"
        return '0x' + hashlib.sha256(raw.encode()).hexdigest()


class IPFSRecord(models.Model):
    evidence  = models.ForeignKey('tap_evidence.Evidence', on_delete=models.CASCADE, related_name='ipfs_records')
    cid       = models.CharField(max_length=100)
    gateway_url = models.URLField(blank=True)
    pinned    = models.BooleanField(default=False)
    size_bytes= models.BigIntegerField(default=0)
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tap_ipfs_records'

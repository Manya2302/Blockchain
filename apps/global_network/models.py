"""TAP-DEV Phase 5 — Global Decentralized Forensic Network"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class ForensicNode(models.Model):
    """A node in the global forensic network (country/org/agency)."""
    NODE_TYPE = [('GOVERNMENT','Government'),('LAW_ENFORCEMENT','Law Enforcement'),
                 ('COURT','Court System'),('ENTERPRISE','Enterprise'),('UNIVERSITY','University'),
                 ('HOSPITAL','Hospital'),('MILITARY','Military'),('INTERPOL','Interpol'),]
    CHAIN_CHOICES = [('ETHEREUM','Ethereum'),('POLYGON','Polygon'),('HYPERLEDGER','Hyperledger Fabric'),
                     ('SOLANA','Solana'),('AVALANCHE','Avalanche'),('COSMOS','Cosmos IBC'),]
    STATUS = [('ACTIVE','Active'),('OFFLINE','Offline'),('SYNCING','Syncing'),('COMPROMISED','Compromised')]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name          = models.CharField(max_length=200)
    node_type     = models.CharField(max_length=20, choices=NODE_TYPE)
    country_code  = models.CharField(max_length=3)
    country_name  = models.CharField(max_length=80)
    city          = models.CharField(max_length=80, blank=True)
    status        = models.CharField(max_length=15, choices=STATUS, default='ACTIVE')
    blockchain    = models.CharField(max_length=20, choices=CHAIN_CHOICES, default='ETHEREUM')
    node_address  = models.CharField(max_length=200)  # RPC/endpoint
    public_key    = models.TextField()                 # post-quantum public key
    did_identifier = models.CharField(max_length=200, blank=True)  # W3C DID
    geo_lat       = models.FloatField(null=True, blank=True)
    geo_lon       = models.FloatField(null=True, blank=True)
    joined_at     = models.DateTimeField(auto_now_add=True)
    last_sync     = models.DateTimeField(null=True, blank=True)
    evidence_count = models.BigIntegerField(default=0)
    trust_score   = models.FloatField(default=100.0)
    metadata      = models.JSONField(default=dict)

    class Meta:
        db_table = 'tap_forensic_nodes'
        ordering = ['country_name', 'name']

    def __str__(self): return f"{self.name} [{self.country_code}] ({self.blockchain})"

    @property
    def status_color(self):
        return {'ACTIVE':'#10b981','OFFLINE':'#6b7280','SYNCING':'#f59e0b','COMPROMISED':'#ef4444'}.get(self.status,'#6b7280')


class CrossChainTransfer(models.Model):
    """Evidence transfer between two forensic nodes on different chains."""
    STATUS = [('PENDING','Pending'),('BRIDGING','Bridging'),('CONFIRMED','Confirmed'),('FAILED','Failed'),('REVERTED','Reverted')]

    transfer_id   = models.UUIDField(default=uuid.uuid4, unique=True)
    source_node   = models.ForeignKey(ForensicNode, on_delete=models.CASCADE, related_name='outbound')
    target_node   = models.ForeignKey(ForensicNode, on_delete=models.CASCADE, related_name='inbound')
    evidence      = models.ForeignKey('tap_evidence.Evidence', on_delete=models.CASCADE, related_name='cross_chain')
    source_chain  = models.CharField(max_length=20)
    target_chain  = models.CharField(max_length=20)
    bridge_protocol = models.CharField(max_length=50, default='IBC')
    status        = models.CharField(max_length=15, choices=STATUS, default='PENDING')
    source_tx_hash = models.CharField(max_length=100, blank=True)
    target_tx_hash = models.CharField(max_length=100, blank=True)
    initiated_at  = models.DateTimeField(auto_now_add=True)
    confirmed_at  = models.DateTimeField(null=True, blank=True)
    initiated_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    evidence_hash = models.CharField(max_length=64)
    attestation   = models.TextField(blank=True)  # cryptographic attestation

    class Meta:
        db_table = 'tap_cross_chain_transfers'
        ordering = ['-initiated_at']

    def __str__(self): return f"Transfer {self.transfer_id} {self.source_chain}→{self.target_chain} [{self.status}]"

    @property
    def status_color(self):
        return {'PENDING':'#f59e0b','BRIDGING':'#00d4ff','CONFIRMED':'#10b981','FAILED':'#ef4444','REVERTED':'#dc2626'}.get(self.status,'#6b7280')


class NetworkConsortiumMember(models.Model):
    """Verified member of the global forensic consortium."""
    organization  = models.ForeignKey('tap_org.Organization', on_delete=models.CASCADE)
    forensic_node = models.ForeignKey(ForensicNode, on_delete=models.CASCADE)
    joined_at     = models.DateTimeField(auto_now_add=True)
    verification_level = models.IntegerField(default=1)  # 1-5
    dao_votes_cast = models.IntegerField(default=0)
    reputation_score = models.FloatField(default=1.0)

    class Meta:
        db_table = 'tap_consortium_members'

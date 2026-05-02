"""
TAP-DEV Blockchain Simulator
Simulates Ethereum/Hyperledger anchoring without a live node.
Phase 3: Replace simulate_* methods with real Web3.py calls.

Solidity contract interface (Phase 3):
  function storeEvidence(bytes32 evidenceHash, bytes32 eventHash, uint256 timestamp) external;
  function verifyEvidence(bytes32 evidenceHash) external view returns (bool, uint256);
"""
import hashlib, time, random
from django.utils import timezone
from .models import BlockchainTransaction, IPFSRecord


class BlockchainSimulator:
    """
    Simulates blockchain anchoring.
    Phase 3 upgrade: replace with Web3.py + deployed Solidity contract.
    """
    NETWORK = 'ETHEREUM_SIM'
    BASE_BLOCK = 19_000_000

    def anchor_evidence(self, evidence, event=None, user=None):
        """Create a simulated blockchain transaction for an evidence hash."""
        data_hash = evidence.sha256_hash
        tx_hash   = BlockchainTransaction.simulate_tx_hash(data_hash)
        block_num = self.BASE_BLOCK + random.randint(1, 50000)
        gas_used  = random.randint(21000, 65000)

        tx = BlockchainTransaction.objects.create(
            evidence=evidence,
            event=event,
            tx_hash=tx_hash,
            block_number=block_num,
            network=self.NETWORK,
            status='CONFIRMED',
            gas_used=gas_used,
            data_hash=data_hash,
            submitter=user,
            metadata={
                'evidence_title': evidence.title,
                'sha256': evidence.sha256_hash,
                'event_type': event.event_type if event else 'ANCHOR',
                'simulated': True,
                # Phase 3: replace with real contract ABI call data
                'contract_call': 'storeEvidence(bytes32,bytes32,uint256)',
            }
        )
        # Update evidence blockchain_tx reference
        evidence.blockchain_tx = tx_hash
        evidence.save(update_fields=['blockchain_tx'])
        return tx


class IPFSSimulator:
    """
    Simulates IPFS pinning. Phase 3 upgrade: replace with ipfshttpclient calls.
    """
    GATEWAY = 'https://ipfs.io/ipfs/'

    def pin_evidence(self, evidence):
        """Simulate uploading file to IPFS and getting a CID."""
        # Generate deterministic fake CID from hash
        raw = f"tapdev-{evidence.sha256_hash}-{evidence.id}"
        fake_cid = 'Qm' + hashlib.sha256(raw.encode()).hexdigest()[:44]

        record = IPFSRecord.objects.create(
            evidence=evidence,
            cid=fake_cid,
            gateway_url=f"{self.GATEWAY}{fake_cid}",
            pinned=True,
            size_bytes=evidence.file_size,
        )
        # Update evidence ipfs_cid field
        evidence.ipfs_cid = fake_cid
        evidence.save(update_fields=['ipfs_cid'])
        return record

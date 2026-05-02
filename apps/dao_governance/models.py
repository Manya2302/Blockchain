"""TAP-DEV Phase 5 — DAO Governance Protocol"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class GovernanceProposal(models.Model):
    STATUS = [("DRAFT","Draft"),("ACTIVE","Active Voting"),("PASSED","Passed"),("REJECTED","Rejected"),("EXECUTED","Executed")]
    PROPOSAL_TYPE = [("PROTOCOL_UPGRADE","Protocol Upgrade"),("STANDARD_CHANGE","Verification Standard"),
                     ("NODE_ADMISSION","Node Admission"),("PARAMETER_CHANGE","Parameter Change"),
                     ("EMERGENCY","Emergency Action"),("BUDGET","Treasury Budget"),("RULE","Rule Amendment")]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal_type = models.CharField(max_length=20, choices=PROPOSAL_TYPE)
    title       = models.CharField(max_length=300)
    description = models.TextField()
    technical_spec = models.TextField(blank=True)
    proposer    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="proposals")
    status      = models.CharField(max_length=15, choices=STATUS, default="DRAFT")
    created_at  = models.DateTimeField(auto_now_add=True)
    voting_start = models.DateTimeField(null=True, blank=True)
    voting_end  = models.DateTimeField(null=True, blank=True)
    votes_for   = models.IntegerField(default=0)
    votes_against = models.IntegerField(default=0)
    votes_abstain = models.IntegerField(default=0)
    quorum_required = models.IntegerField(default=51)  # percent
    pass_threshold  = models.IntegerField(default=67)  # percent supermajority
    executed_at = models.DateTimeField(null=True, blank=True)
    on_chain_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "tap_dao_proposals"
        ordering = ["-created_at"]

    def __str__(self): return f"[{self.proposal_type}] {self.title[:60]}"

    @property
    def total_votes(self): return self.votes_for + self.votes_against + self.votes_abstain

    @property
    def approval_rate(self):
        t = self.votes_for + self.votes_against
        return round(self.votes_for / t * 100, 1) if t > 0 else 0

    @property
    def passed(self): return self.votes_for >= (self.total_votes * self.pass_threshold / 100)


class DAOVote(models.Model):
    VOTE_CHOICE = [("FOR","For"),("AGAINST","Against"),("ABSTAIN","Abstain")]

    proposal  = models.ForeignKey(GovernanceProposal, on_delete=models.CASCADE, related_name="votes")
    voter     = models.ForeignKey(User, on_delete=models.CASCADE)
    choice    = models.CharField(max_length=10, choices=VOTE_CHOICE)
    weight    = models.FloatField(default=1.0)  # governance token weight
    voted_at  = models.DateTimeField(auto_now_add=True)
    rationale = models.TextField(blank=True)
    on_chain_tx = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "tap_dao_votes"
        unique_together = ("proposal", "voter")

    def __str__(self): return f"{self.voter.username} voted {self.choice} on {self.proposal.title[:30]}"

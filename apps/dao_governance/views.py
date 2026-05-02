"""TAP-DEV Phase 5 — DAO Governance Views"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import GovernanceProposal, DAOVote

@login_required
def dao_dashboard(request):
    _seed_proposals()
    proposals = GovernanceProposal.objects.order_by("-created_at")
    active    = proposals.filter(status="ACTIVE").count()
    passed    = proposals.filter(status="PASSED").count()
    my_votes  = DAOVote.objects.filter(voter=request.user).count()
    return render(request, "dao_governance/dashboard.html", {
        "proposals": proposals[:20], "active": active, "passed": passed, "my_votes": my_votes,
        "proposal_types": GovernanceProposal.PROPOSAL_TYPE,
    })

@login_required
def proposal_detail(request, proposal_id):
    proposal = get_object_or_404(GovernanceProposal, id=proposal_id)
    my_vote  = DAOVote.objects.filter(proposal=proposal, voter=request.user).first()
    votes    = DAOVote.objects.filter(proposal=proposal).order_by("-voted_at")[:20]
    return render(request, "dao_governance/proposal.html", {
        "proposal": proposal, "my_vote": my_vote, "votes": votes,
    })

@login_required
def cast_vote(request, proposal_id):
    proposal = get_object_or_404(GovernanceProposal, id=proposal_id)
    if request.method == "POST":
        if DAOVote.objects.filter(proposal=proposal, voter=request.user).exists():
            messages.warning(request, "You have already voted on this proposal.")
        elif proposal.status != "ACTIVE":
            messages.error(request, "This proposal is not open for voting.")
        else:
            choice = request.POST.get("choice","ABSTAIN")
            import hashlib, secrets
            DAOVote.objects.create(
                proposal=proposal, voter=request.user, choice=choice,
                rationale=request.POST.get("rationale",""),
                on_chain_tx="0x"+hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:40],
            )
            if choice == "FOR": proposal.votes_for += 1
            elif choice == "AGAINST": proposal.votes_against += 1
            else: proposal.votes_abstain += 1
            if proposal.passed: proposal.status = "PASSED"
            proposal.save()
            messages.success(request, f'Vote cast: {choice} on "{proposal.title[:40]}"')
    return redirect("dao_governance:proposal", proposal_id=proposal_id)

@login_required
def create_proposal(request):
    if request.method == "POST":
        import hashlib, secrets
        proposal = GovernanceProposal.objects.create(
            proposal_type=request.POST.get("proposal_type","PROTOCOL_UPGRADE"),
            title=request.POST["title"],
            description=request.POST.get("description",""),
            technical_spec=request.POST.get("technical_spec",""),
            proposer=request.user, status="ACTIVE",
            voting_start=timezone.now(),
            voting_end=timezone.now()+timezone.timedelta(days=7),
            on_chain_hash="0x"+hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:40],
        )
        messages.success(request, f"Proposal submitted and voting opened for 7 days.")
        return redirect("dao_governance:proposal", proposal_id=proposal.id)
    return render(request, "dao_governance/create.html", {
        "proposal_types": GovernanceProposal.PROPOSAL_TYPE,
    })

def _seed_proposals():
    if GovernanceProposal.objects.exists(): return
    import random
    proposals_data = [
        ("PROTOCOL_UPGRADE","TAP-DEV Phase 6 Cross-Chain Bridge Upgrade","Upgrade bridge from TAP-IBC v1 to TAP-IBC v2 for 50% lower gas costs and Solana support.",100,67,45,5,2),
        ("STANDARD_CHANGE","NIST Level 5 Mandatory for Government Nodes","Require all government forensic nodes to use CRYSTALS-Dilithium NIST Level 5 by Q3 2026.",52,72,38,8,6),
        ("NODE_ADMISSION","Interpol Node Admission to Global Consortium","Admit Interpol as a verified node in the TAP-DEV global forensic network.",89,63,71,4,1),
        ("EMERGENCY","Emergency: Patch Cross-Chain Replay Vulnerability","Critical patch for replay attack vector in cross-chain transfer protocol.",120,75,88,12,8),
        ("BUDGET","Q2 2026 Developer Ecosystem Grant Program","Allocate 50,000 TAP tokens for developer grants and SDK improvements.",44,55,31,3,4),
    ]
    from django.contrib.auth.models import User
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user: return
    for ptype,title,desc,vf,va,vab,quorum,threshold in proposals_data:
        GovernanceProposal.objects.create(
            proposal_type=ptype, title=title, description=desc, proposer=user,
            status=random.choice(["ACTIVE","PASSED","ACTIVE"]),
            votes_for=vf, votes_against=va, votes_abstain=vab,
            voting_start=timezone.now()-timezone.timedelta(days=3),
            voting_end=timezone.now()+timezone.timedelta(days=4),
        )

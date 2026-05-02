"""TAP-DEV Phase 4+ — Zero-Knowledge Proof Views (Enhanced)
Adds Resume Verification workflow, Trusted Issuer management, and Verification Logs."""
import json, hashlib, secrets
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import ZKPVerification, TrustedIssuer, ResumeCredential, VerificationLog


def _log_verification(credential=None, zkp_proof=None, action='VERIFY',
                      actor=None, request=None, detail='', success=True):
    """Create a verification audit log entry."""
    from apps.users.utils import get_client_ip
    ip = get_client_ip(request) if request else None
    VerificationLog.objects.create(
        credential=credential, zkp_proof=zkp_proof,
        action=action, actor=actor, ip_address=ip,
        detail=detail, success=success,
    )


# ── Core ZKP Views (preserved) ──────────────────────────────────────

@login_required
def zkp_dashboard(request):
    proofs = ZKPVerification.objects.select_related('evidence', 'created_by').order_by('-created_at')
    valid_ct = proofs.filter(status='VALID').count()
    pending_ct = proofs.filter(status='PENDING').count()
    invalid_ct = proofs.filter(status='INVALID').count()

    # Resume stats
    credentials = ResumeCredential.objects.filter(owner=request.user)
    cred_stats = {
        'total': credentials.count(),
        'verified': credentials.filter(status='VERIFIED').count(),
        'pending': credentials.filter(status='PENDING').count(),
    }
    issuers = TrustedIssuer.objects.filter(trust_level__in=['VERIFIED', 'TRUSTED']).count()

    return render(request, 'zkp/dashboard.html', {
        'proofs': proofs[:30],
        'stats': {'total': proofs.count(), 'valid': valid_ct, 'pending': pending_ct, 'invalid': invalid_ct},
        'cred_stats': cred_stats,
        'issuer_count': issuers,
    })


@login_required
def create_proof(request, evidence_id):
    from apps.evidence.models import Evidence
    evidence = get_object_or_404(Evidence, pk=evidence_id)
    if request.method == 'POST':
        commitment, salt = ZKPVerification.generate_commitment(evidence.sha256_hash)
        proof_id = ZKPVerification.generate_proof_id(evidence.sha256_hash)
        nullifier = hashlib.sha256(f"{proof_id}{salt}".encode()).hexdigest()[:32]
        use_case = request.POST.get('use_case', 'DOCUMENT_AUTH')
        public_inputs = {
            'document_title':   evidence.title,
            'submission_date':  evidence.created_at.strftime('%Y-%m-%d'),
            'submitter_org':    getattr(getattr(request.user, 'profile', None), 'organization', ''),
            'hash_prefix':      evidence.sha256_hash[:8] + '...',
            'chain_length':     evidence.events.count(),
            'trust_score':      evidence.trust_score,
        }
        verify_url = f"{request.build_absolute_uri('/zkp/verify/')}{proof_id}/"
        qr_data = json.dumps({'proof_id': proof_id, 'verify_url': verify_url, 'commitment': commitment[:16]})

        proof = ZKPVerification.objects.create(
            evidence=evidence, use_case=use_case, proof_id=proof_id,
            commitment=commitment, nullifier=nullifier,
            public_inputs=public_inputs, status='VALID',
            created_by=request.user,
            expires_at=timezone.now() + timezone.timedelta(days=365),
            qr_code_data=qr_data, verification_url=verify_url,
        )

        _log_verification(zkp_proof=proof, action='SUBMIT', actor=request.user,
                          request=request, detail=f"Created ZKP proof for '{evidence.title}'")

        messages.success(request, f'ZKP Proof #{proof_id[:12]}... created. Document authenticity verified without revealing content.')
        return redirect('zkp:detail', proof_id=proof_id)
    return render(request, 'zkp/create.html', {
        'evidence': evidence, 'use_cases': ZKPVerification.USE_CASE,
    })


@login_required
def proof_detail(request, proof_id):
    proof = get_object_or_404(ZKPVerification, proof_id=proof_id)
    logs = VerificationLog.objects.filter(zkp_proof=proof).order_by('-timestamp')[:20]
    return render(request, 'zkp/detail.html', {'proof': proof, 'logs': logs})


def public_verify(request, proof_id):
    """Public verification endpoint — no login required."""
    proof = ZKPVerification.objects.filter(proof_id=proof_id).first()
    valid = proof is not None and proof.is_valid()
    if proof and valid:
        proof.verified_at = timezone.now()
        proof.verified_by = request.user if request.user.is_authenticated else None
        proof.save(update_fields=['verified_at'])
    _log_verification(zkp_proof=proof, action='VERIFY',
                      actor=request.user if request.user.is_authenticated else None,
                      request=request,
                      detail=f"Public verification: {'VALID' if valid else 'INVALID'}",
                      success=valid)
    return render(request, 'zkp/public_verify.html', {
        'proof': proof, 'valid': valid, 'proof_id': proof_id,
    })


def verify_api(request, proof_id):
    """JSON API for external ZKP verification."""
    proof = ZKPVerification.objects.filter(proof_id=proof_id).first()
    if not proof:
        return JsonResponse({'valid': False, 'error': 'Proof not found'}, status=404)
    return JsonResponse({
        'valid': proof.is_valid(), 'status': proof.status,
        'use_case': proof.use_case, 'public_inputs': proof.public_inputs,
        'expires_at': proof.expires_at.isoformat() if proof.expires_at else None,
    })


# ── Resume Verification Views ───────────────────────────────────────

@login_required
def resume_dashboard(request):
    """Resume credential verification dashboard."""
    credentials = ResumeCredential.objects.filter(
        owner=request.user
    ).select_related('issuer', 'zkp_proof', 'evidence').order_by('-created_at')

    verified = credentials.filter(status='VERIFIED').count()
    pending = credentials.filter(status='PENDING').count()
    failed = credentials.filter(status='FAILED').count()

    return render(request, 'zkp/resume_dashboard.html', {
        'credentials': credentials,
        'stats': {'total': credentials.count(), 'verified': verified, 'pending': pending, 'failed': failed},
    })


@login_required
def submit_credential(request):
    """Submit a new credential for ZKP verification."""
    from apps.evidence.models import Evidence

    if request.method == 'POST':
        claim_type = request.POST.get('claim_type', 'DEGREE')
        claim_title = request.POST.get('claim_title', '').strip()
        claim_detail = request.POST.get('claim_detail', '').strip()
        issuer_name = request.POST.get('issuer_name', '').strip()
        evidence_id = request.POST.get('evidence_id')

        if not claim_title:
            messages.error(request, 'Claim title is required.')
            return redirect('zkp:submit_credential')

        # Link to evidence if provided
        evidence = None
        document_hash = ''
        if evidence_id:
            try:
                evidence = Evidence.objects.get(pk=evidence_id, uploader=request.user)
                document_hash = evidence.sha256_hash
            except Evidence.DoesNotExist:
                pass

        # Find or create issuer
        issuer = None
        if issuer_name:
            issuer_hash = TrustedIssuer.compute_issuer_hash(issuer_name, 'UNIVERSITY')
            issuer = TrustedIssuer.objects.filter(issuer_hash=issuer_hash).first()

        # Create credential
        cred = ResumeCredential(
            owner=request.user,
            claim_type=claim_type,
            claim_title=claim_title,
            claim_detail=claim_detail,
            issuer=issuer,
            issuer_name=issuer_name or (issuer.name if issuer else ''),
            evidence=evidence,
            document_hash=document_hash or hashlib.sha256(
                f"{claim_title}{claim_type}{request.user.pk}".encode()
            ).hexdigest(),
        )
        cred.generate_commitment()

        # Auto-verify if issuer is trusted and evidence has good trust score
        if issuer and issuer.trust_level in ('VERIFIED', 'TRUSTED'):
            if evidence and evidence.trust_score >= 80:
                cred.status = 'VERIFIED'
                cred.verified_at = timezone.now()
            else:
                cred.status = 'PENDING'
        else:
            cred.status = 'PENDING'

        cred.save()

        # Generate ZKP proof for the credential
        if evidence:
            commitment, salt = ZKPVerification.generate_commitment(cred.document_hash)
            proof_id = ZKPVerification.generate_proof_id(cred.document_hash)
            nullifier = hashlib.sha256(f"{proof_id}{salt}".encode()).hexdigest()[:32]
            verify_url = f"{request.build_absolute_uri('/zkp/verify/')}{proof_id}/"
            qr_data = json.dumps({
                'proof_id': proof_id, 'verify_url': verify_url,
                'claim_type': claim_type, 'commitment': commitment[:16]
            })

            proof = ZKPVerification.objects.create(
                evidence=evidence, use_case='RESUME' if claim_type in ('DEGREE', 'DIPLOMA') else 'SKILL_CERT',
                proof_id=proof_id, commitment=commitment, nullifier=nullifier,
                public_inputs={
                    'claim_type': cred.get_claim_type_display(),
                    'claim_title': claim_title,
                    'issuer': issuer_name or 'Unknown',
                    'issuer_trust': issuer.trust_level if issuer else 'UNVERIFIED',
                    'submission_date': cred.created_at.strftime('%Y-%m-%d') if cred.created_at else '',
                },
                status='VALID' if cred.status == 'VERIFIED' else 'PENDING',
                created_by=request.user,
                expires_at=timezone.now() + timezone.timedelta(days=365),
                qr_code_data=qr_data, verification_url=verify_url,
            )
            cred.zkp_proof = proof
            cred.save(update_fields=['zkp_proof'])

        _log_verification(credential=cred, action='SUBMIT', actor=request.user,
                          request=request, detail=f"Submitted credential: {claim_title}")

        from apps.notifications.models import Notification
        Notification.objects.create(
            user=request.user, title='Credential Submitted',
            message=f'Your credential "{claim_title}" has been submitted for verification.',
            notif_type='SUCCESS', link='/zkp/resume/',
        )

        messages.success(request, f'Credential "{claim_title}" submitted for verification.')
        return redirect('zkp:resume_dashboard')

    # GET: show form
    user_evidence = Evidence.objects.filter(uploader=request.user, is_latest_version=True).order_by('-created_at')
    issuers = TrustedIssuer.objects.filter(trust_level__in=['VERIFIED', 'TRUSTED']).order_by('name')
    return render(request, 'zkp/submit_credential.html', {
        'claim_types': ResumeCredential.CLAIM_TYPE,
        'user_evidence': user_evidence,
        'issuers': issuers,
    })


@login_required
def verify_credential(request, credential_id):
    """Verify a credential (analyst/admin only)."""
    role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
    if role not in ('ANALYST', 'ADMIN'):
        messages.error(request, 'Only analysts can verify credentials.')
        return redirect('zkp:resume_dashboard')

    cred = get_object_or_404(ResumeCredential, pk=credential_id)

    if request.method == 'POST':
        action = request.POST.get('action', 'approve')
        if action == 'approve':
            cred.status = 'VERIFIED'
            cred.verified_at = timezone.now()
            cred.verified_by = request.user
            cred.save()
            if cred.zkp_proof:
                cred.zkp_proof.status = 'VALID'
                cred.zkp_proof.verified_at = timezone.now()
                cred.zkp_proof.verified_by = request.user
                cred.zkp_proof.save()
            _log_verification(credential=cred, action='APPROVE', actor=request.user,
                              request=request, detail=f"Approved: {cred.claim_title}")

            from apps.notifications.models import Notification
            Notification.objects.create(
                user=cred.owner, title='Credential Verified ✓',
                message=f'Your credential "{cred.claim_title}" has been verified by {request.user.username}.',
                notif_type='SUCCESS', link='/zkp/resume/',
            )
            messages.success(request, f'Credential "{cred.claim_title}" verified.')
        else:
            cred.status = 'FAILED'
            cred.save()
            if cred.zkp_proof:
                cred.zkp_proof.status = 'INVALID'
                cred.zkp_proof.save()
            _log_verification(credential=cred, action='REJECT', actor=request.user,
                              request=request, detail=f"Rejected: {cred.claim_title}", success=False)

            from apps.notifications.models import Notification
            Notification.objects.create(
                user=cred.owner, title='Credential Rejected',
                message=f'Your credential "{cred.claim_title}" has been rejected.',
                notif_type='WARNING', link='/zkp/resume/',
            )
            messages.warning(request, f'Credential "{cred.claim_title}" rejected.')

        return redirect('zkp:credential_detail', credential_id=credential_id)

    return render(request, 'zkp/verify_credential.html', {'cred': cred})


@login_required
def credential_detail(request, credential_id):
    """View credential details with verification status."""
    cred = get_object_or_404(ResumeCredential, pk=credential_id)
    # Only owner or analyst can view
    role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
    if cred.owner != request.user and role not in ('ANALYST', 'ADMIN'):
        messages.error(request, 'Access denied.')
        return redirect('zkp:resume_dashboard')

    logs = VerificationLog.objects.filter(credential=cred).order_by('-timestamp')[:20]
    return render(request, 'zkp/credential_detail.html', {
        'cred': cred,
        'logs': logs,
        'is_analyst': role in ('ANALYST', 'ADMIN'),
    })


@login_required
def manage_issuers(request):
    """Manage trusted issuers (admin only)."""
    role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
    if role != 'ADMIN':
        messages.error(request, 'Admin access required.')
        return redirect('zkp:dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        issuer_type = request.POST.get('issuer_type', 'UNIVERSITY')
        website = request.POST.get('website', '').strip()
        country = request.POST.get('country', '').strip()
        trust_level = request.POST.get('trust_level', 'PENDING')

        if not name:
            messages.error(request, 'Issuer name is required.')
            return redirect('zkp:manage_issuers')

        issuer_hash = TrustedIssuer.compute_issuer_hash(name, issuer_type)
        if TrustedIssuer.objects.filter(issuer_hash=issuer_hash).exists():
            messages.warning(request, f'Issuer "{name}" already exists.')
            return redirect('zkp:manage_issuers')

        TrustedIssuer.objects.create(
            name=name, issuer_type=issuer_type, trust_level=trust_level,
            issuer_hash=issuer_hash, website=website, country=country,
            created_by=request.user,
            verified_at=timezone.now() if trust_level in ('VERIFIED', 'TRUSTED') else None,
        )
        messages.success(request, f'Issuer "{name}" added successfully.')
        return redirect('zkp:manage_issuers')

    issuers = TrustedIssuer.objects.all().order_by('-created_at')
    pending_creds = ResumeCredential.objects.filter(status='PENDING').select_related('owner', 'issuer')
    return render(request, 'zkp/manage_issuers.html', {
        'issuers': issuers,
        'pending_creds': pending_creds,
        'issuer_types': TrustedIssuer.ISSUER_TYPE,
        'trust_levels': TrustedIssuer.TRUST_LEVEL,
    })


@login_required
def verification_logs(request):
    """View all verification audit logs."""
    role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
    if role not in ('ANALYST', 'ADMIN'):
        messages.error(request, 'Analyst access required.')
        return redirect('zkp:dashboard')

    logs = VerificationLog.objects.select_related(
        'credential', 'zkp_proof', 'actor'
    ).order_by('-timestamp')[:100]
    return render(request, 'zkp/verification_logs.html', {'logs': logs})

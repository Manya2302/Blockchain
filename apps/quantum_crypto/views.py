"""TAP-DEV Phase 5 — Quantum-Resistant Cryptography Views"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import QuantumSignature

def analyst_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,"profile",None),"role","") in ("ANALYST","ADMIN"):
            return fn(request, *args, **kwargs)
        messages.error(request,"Access denied."); return redirect("dashboard:home")
    return wrap

@analyst_required
def qcrypto_dashboard(request):
    sigs = QuantumSignature.objects.select_related("evidence","created_by").order_by("-created_at")
    valid = sigs.filter(is_valid=True).count()
    by_algo = {}
    for s in sigs[:200]:
        by_algo[s.algorithm] = by_algo.get(s.algorithm, 0) + 1
    return render(request, "quantum_crypto/dashboard.html", {
        "sigs": sigs[:30], "valid": valid, "total": sigs.count(),
        "by_algo": by_algo, "algorithms": QuantumSignature.ALGORITHM,
    })

@analyst_required
def sign_evidence(request, evidence_id):
    from apps.evidence.models import Evidence
    evidence = get_object_or_404(Evidence, pk=evidence_id)
    if request.method == "POST":
        algorithm = request.POST.get("algorithm", "CRYSTALS_DILITHIUM")
        security_level = int(request.POST.get("security_level", 3))
        pk, sk_hash, params = QuantumSignature.generate_pq_keypair(algorithm)
        sig = QuantumSignature.sign_evidence(evidence.sha256_hash, sk_hash, algorithm)
        QuantumSignature.objects.create(
            evidence=evidence, algorithm=algorithm, security_level=security_level,
            public_key_hash=pk[:64], signature_hash=sig,
            lattice_params=params, created_by=request.user, is_valid=True,
        )
        messages.success(request, f"Post-quantum signature created using {algorithm} at NIST Level {security_level}")
        return redirect("evidence:detail", pk=evidence_id)
    return render(request, "quantum_crypto/sign.html", {
        "evidence": evidence, "algorithms": QuantumSignature.ALGORITHM,
        "security_levels": QuantumSignature.SECURITY_LEVEL,
    })

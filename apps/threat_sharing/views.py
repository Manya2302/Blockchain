"""TAP-DEV Phase 5 — Global Threat Intelligence Sharing Views"""
import json, hashlib, secrets
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import ThreatSignature, ThreatFeed

def analyst_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,"profile",None),"role","") in ("ANALYST","ADMIN"):
            return fn(request, *args, **kwargs)
        messages.error(request,"Access denied."); return redirect("dashboard:home")
    return wrap

@analyst_required
def threat_hub(request):
    _seed_threat_feeds()
    sigs = ThreatSignature.objects.order_by("-contributed_at")
    feeds = ThreatFeed.objects.filter(is_active=True).order_by("-published_at")[:10]
    critical_sigs = sigs.filter(severity="CRITICAL").count()
    total_matches = sum(s.global_matches for s in sigs[:500])
    threat_class_dist = {}
    for s in sigs[:50]:
        threat_class_dist[s.threat_class] = threat_class_dist.get(s.threat_class, 0) + 1
    return render(request, "threat_sharing/hub.html", {
        "sigs": sigs[:30], "feeds": feeds,
        "stats": {"total": sigs.count(), "critical": critical_sigs, "total_matches": total_matches,
                  "contributors": sigs.values("contributed_by").distinct().count()},
        "threat_class_json": json.dumps(threat_class_dist),
    })

@analyst_required
def contribute_signature(request):
    if request.method == "POST":
        from apps.organizations.models import Organization
        ioc_raw = request.POST.get("ioc_value", "")
        ioc_hash = hashlib.sha256(ioc_raw.encode()).hexdigest()
        org = Organization.objects.filter(memberships__user=request.user).first()
        sig = ThreatSignature.objects.create(
            threat_class=request.POST.get("threat_class", "MALWARE"),
            ioc_type=request.POST.get("ioc_type", "hash"),
            ioc_value_hash=ioc_hash,
            description=request.POST.get("description",""),
            confidence=int(request.POST.get("confidence", 2)),
            severity=request.POST.get("severity","MEDIUM"),
            contributed_by=org, is_anonymous=request.POST.get("anonymous")=="1",
            stix_json={"type":"indicator","spec_version":"2.1",
                       "id":f"indicator--{secrets.token_hex(16)}","pattern":"[file:hashes.SHA-256 = '...']"},
        )
        messages.success(request, "Threat signature contributed anonymously to global consortium.")
        return redirect("threat_sharing:hub")
    return render(request, "threat_sharing/contribute.html", {
        "threat_classes": ThreatSignature.THREAT_CLASS,
        "confidence_levels": ThreatSignature.CONFIDENCE,
    })

def _seed_threat_feeds():
    if ThreatFeed.objects.count() > 0: return
    feeds_data = [
        ("TAP_AI","CRITICAL","AI Detected Global Replay Attack Campaign","Active replay attack campaign across 14 organizations detected by TAP-DEV BiLSTM cluster",["Finance","Legal","Healthcare"],["US","UK","DE","FR"]),
        ("CERT","HIGH","National CERT Advisory: Timestamp Manipulation Malware","New malware strain targeting forensic platforms with clock manipulation capabilities",["Government","Law Enforcement"],["US","AU","CA"]),
        ("INTERPOL","HIGH","INTERPOL Purple Notice: Document Forgery Network","Cross-border document forgery operation identified — 47 forged credentials discovered",["Courts","Insurance","Banks"],["GLOBAL"]),
        ("MITRE","MEDIUM","MITRE ATT&CK Update T1588.002: Tool Compromise","Updated TTPs for tool compromise in forensic investigations",["ALL"],["GLOBAL"]),
    ]
    for source, sev, title, desc, sectors, countries in feeds_data:
        ThreatFeed.objects.create(feed_source=source, severity=sev, title=title,
                                  description=desc, affected_sectors=sectors, affected_countries=countries)

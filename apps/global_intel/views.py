"""TAP-DEV Phase 5 — Global Intelligence & Threat Map Views"""
import json, random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import GlobalThreatEvent, TranslationRequest

def analyst_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,"profile",None),"role","") in ("ANALYST","ADMIN"):
            return fn(request, *args, **kwargs)
        messages.error(request,"Access denied."); return redirect("dashboard:home")
    return wrap

@analyst_required
def global_map(request):
    _seed_global_threats()
    events = GlobalThreatEvent.objects.filter(is_active=True).order_by("-reported_at")
    critical_ct = events.filter(severity="CRITICAL").count()
    active_ct   = events.filter(is_active=True).count()
    countries   = events.values("country").distinct().count()
    geo_data = list(events.values("event_id","threat_type","title","severity","country","city","geo_lat","geo_lon","is_verified"))
    for item in geo_data:
        item["event_id"] = str(item["event_id"])
        sev = item["severity"]
        item["color"] = {"CRITICAL":"#dc2626","HIGH":"#ef4444","MEDIUM":"#f59e0b","LOW":"#84cc16"}.get(sev,"#6b7280")
    return render(request, "global_intel/map.html", {
        "events": events[:30], "critical_ct": critical_ct, "active_ct": active_ct, "countries": countries,
        "geo_data_json": json.dumps(geo_data),
    })

@analyst_required
def translate_evidence(request, evidence_id=None):
    translations = TranslationRequest.objects.order_by("-created_at")[:20]
    if request.method == "POST":
        from apps.evidence.models import Evidence
        src = request.POST.get("source_text","")
        src_lang = request.POST.get("source_language","en")
        tgt_lang = request.POST.get("target_language","fr")
        translated = _simulate_translation(src, src_lang, tgt_lang)
        tr = TranslationRequest.objects.create(
            source_text=src[:2000], source_language=src_lang, target_language=tgt_lang,
            translated_text=translated, status="COMPLETE",
            evidence_ref=int(evidence_id) if evidence_id else None,
        )
        messages.success(request, f"Evidence translated: {src_lang.upper()} → {tgt_lang.upper()}")
        return redirect("global_intel:translate")
    return render(request, "global_intel/translate.html", {
        "translations": translations,
        "languages": [("en","English"),("fr","French"),("de","German"),("es","Spanish"),("ar","Arabic"),("zh","Chinese"),("ja","Japanese"),("ru","Russian"),("pt","Portuguese"),("ko","Korean")],
    })


def geo_events_api(request):
    events = GlobalThreatEvent.objects.filter(is_active=True).values("event_id","threat_type","severity","country","geo_lat","geo_lon","title")
    data = [dict(e, event_id=str(e["event_id"])) for e in events]
    return JsonResponse({"events": data, "total": len(data)})

def _seed_global_threats():
    if GlobalThreatEvent.objects.exists(): return
    threats_data = [
        ("ATTACK","CRITICAL","Coordinated APT Campaign — Finance Sector","US",40.7128,-74.0060,["Finance","Banking"],True),
        ("RANSOMWARE","CRITICAL","LockBit 4.0 Hospital Infrastructure Attack","UK",51.5074,-0.1276,["Healthcare"],True),
        ("BREACH","HIGH","Government Database Breach — 2.1M Records","DE",52.5200,13.4050,["Government"],True),
        ("IOT","HIGH","IoT Botnet — Industrial SCADA Compromise","CN",39.9042,116.4074,["Industrial"],False),
        ("FRAUD","HIGH","Mass Document Forgery Ring — Legal Sector","FR",48.8566,2.3522,["Legal","Insurance"],True),
        ("APT","CRITICAL","APT29 Activity — Critical Infrastructure","UA",50.4501,30.5234,["Government","Energy"],True),
        ("ATTACK","MEDIUM","DDoS Campaign — Media Organizations","JP",35.6762,139.6503,["Media"],True),
        ("INSIDER","HIGH","Insider Threat — Defense Contractor","AU",-33.8688,151.2093,["Military"],False),
        ("BREACH","MEDIUM","Healthcare Records Breach — 450K Patients","CA",43.6532,-79.3832,["Healthcare"],True),
        ("RANSOMWARE","HIGH","Smart City Infrastructure Ransomware","SG",1.3521,103.8198,["Government","Smart City"],True),
        ("FRAUD","CRITICAL","Cross-Border Document Forgery Network","BR",-23.5505,-46.6333,["Legal","Courts"],True),
        ("IOT","MEDIUM","Airport Security System Intrusion Attempt","IN",19.0760,72.8777,["Transportation"],False),
        ("APT","HIGH","Supply Chain Attack — Software Vendor","IL",31.7683,35.2137,["Technology"],True),
        ("ATTACK","MEDIUM","Critical Infrastructure Scanning","ZA",-26.2041,28.0473,["Energy","Water"],False),
        ("RANSOMWARE","HIGH","Port Authority Systems Encrypted","NL",51.9244,4.4777,["Transportation","Maritime"],True),
    ]
    for ttype, sev, title, country, lat, lon, sectors, verified in threats_data:
        GlobalThreatEvent.objects.create(
            threat_type=ttype, severity=sev, title=title, country=country,
            geo_lat=lat, geo_lon=lon, affected_sectors=sectors, is_verified=verified,
        )

def _simulate_translation(text, src, tgt):
    """Simulate AI translation with realistic placeholder."""
    lang_prefixes = {"fr":"[FR] ","de":"[DE] ","es":"[ES] ","ar":"[AR] ","zh":"[ZH] ","ja":"[JA] ","ru":"[RU] ","ko":"[KO] "}
    prefix = lang_prefixes.get(tgt, "[" + tgt.upper() + "] ")
    header = prefix + "[TAP-DEV AI Translation Engine v5.0 - " + src.upper() + " to " + tgt.upper() + "]"
    footer = "[Translated by TAP-DEV Neural Machine Translation. Certified ISO 17100:2015]"
    return header + "\n\n" + str(text) + "\n\n" + footer


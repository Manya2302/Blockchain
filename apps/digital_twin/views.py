"""TAP-DEV Phase 5 — Digital Twin Simulation Views"""
import json, time, random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import DigitalTwin, TwinSimulation

def admin_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,"profile",None),"role","") == "ADMIN":
            return fn(request, *args, **kwargs)
        messages.error(request,"Admin required."); return redirect("dashboard:home")
    return wrap

def analyst_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,"profile",None),"role","") in ("ANALYST","ADMIN"):
            return fn(request, *args, **kwargs)
        messages.error(request,"Access denied."); return redirect("dashboard:home")
    return wrap

@analyst_required
def twin_dashboard(request):
    _seed_demo_twins()
    twins = DigitalTwin.objects.select_related("organization").order_by("-created_at")
    all_sims_qs = TwinSimulation.objects.select_related("twin").order_by("-started_at")
    detected = all_sims_qs.filter(was_detected=True).count()
    evaded   = all_sims_qs.filter(was_detected=False).count()
    detection_rate = round(detected / max(detected + evaded, 1) * 100, 1)
    sims = all_sims_qs[:20]
    return render(request, "digital_twin/dashboard.html", {
        "twins": twins, "sims": sims,
        "stats": {"total_twins": twins.count(), "simulations": all_sims_qs.count(),
                  "detected": detected, "evaded": evaded, "detection_rate": detection_rate},
    })

@admin_required
def create_twin(request):
    if request.method == "POST":
        from apps.organizations.models import Organization
        org = Organization.objects.filter(memberships__user=request.user).first()
        twin = DigitalTwin.objects.create(
            name=request.POST["name"],
            twin_type=request.POST.get("twin_type","NETWORK"),
            organization=org, created_by=request.user,
            topology={"nodes": 12, "edges": 24, "subnets": 3},
            assets=[{"name":"Web Server","type":"server","criticality":"HIGH"},
                    {"name":"Database","type":"database","criticality":"CRITICAL"},
                    {"name":"Firewall","type":"network","criticality":"HIGH"}],
            vulnerabilities=[{"cve":"CVE-2024-1234","severity":"HIGH","component":"Web Server"}],
        )
        messages.success(request, f"Digital twin '{twin.name}' created successfully.")
        return redirect("digital_twin:dashboard")
    return render(request, "digital_twin/create.html", {"twin_types": DigitalTwin.TWIN_TYPE})

@admin_required
def run_simulation(request, twin_id):
    twin = get_object_or_404(DigitalTwin, id=twin_id)
    if request.method == "POST":
        scenario = request.POST.get("attack_scenario","RANSOMWARE")
        sim = TwinSimulation.objects.create(
            twin=twin, attack_scenario=scenario,
            status="RUNNING", initiated_by=request.user,
        )
        _execute_simulation(sim, twin)
        result = "✓ DETECTED" if sim.was_detected else "✗ EVADED"
        messages.success(request, f"Simulation complete — {result} (AI response score: {sim.ai_response_score:.0%})")
        return redirect("digital_twin:sim_detail", sim_id=sim.id)
    return render(request, "digital_twin/run_sim.html", {
        "twin": twin, "scenarios": TwinSimulation.ATTACK_SCENARIO,
    })

@analyst_required
def sim_detail(request, sim_id):
    sim = get_object_or_404(TwinSimulation, id=sim_id)
    return render(request, "digital_twin/sim_detail.html", {"sim": sim})

def _execute_simulation(sim, twin):
    t_start = time.time()
    scenario = sim.attack_scenario
    kill_chain = {
        "RANSOMWARE": ["Phishing email delivered","Macro executed","Dropper installed","C2 connection","Lateral movement","Encryption initiated"],
        "DDoS": ["Botnet assembled","Target reconnaissance","UDP flood initiated","Application layer attack","Bandwidth exhaustion"],
        "APT_LATERAL": ["Initial compromise","Credential harvesting","Lateral movement","Persistence installed","Data staging","Exfiltration"],
        "SUPPLY_CHAIN": ["Vendor system compromised","Malicious update pushed","Target installation","Backdoor activated","Data access"],
        "INSIDER": ["Privileged account abuse","Bulk data access","USB exfiltration attempt","Log deletion","Cover tracks"],
    }.get(scenario, ["Attack initiated","Execution","Impact"])

    detection_time = random.randint(60, 3600)
    detected = random.random() > 0.35  # 65% detection rate

    sim.kill_chain_steps = [{"step":i+1,"action":a,"detected":detected and i>=len(kill_chain)//2}
                            for i,a in enumerate(kill_chain)]
    sim.affected_assets = random.sample(twin.assets, k=min(random.randint(1,3), len(twin.assets)))
    sim.was_detected = detected
    sim.detection_time = detection_time if detected else 0
    sim.ai_response_score = random.uniform(0.65, 0.95)
    sim.duration_seconds = int(time.time() - t_start)
    sim.status = "COMPLETE"
    sim.completed_at = timezone.now()
    sim.report_data = {
        "scenario": scenario, "detected": detected,
        "mitre_techniques": ["T1566.001","T1059.001","T1053.005"],
        "recommendations": ["Patch CVE-2024-1234","Enable EDR","Review access controls"]
    }
    sim.save()
    twin.total_simulations += 1
    twin.last_simulation = timezone.now()
    twin.save(update_fields=["total_simulations","last_simulation"])

def _seed_demo_twins():
    if DigitalTwin.objects.exists(): return
    from apps.organizations.models import Organization
    org = Organization.objects.first()
    twins = [("Enterprise HQ Network","NETWORK"),("Hospital Patient Systems","HOSPITAL"),
             ("Smart City Infrastructure","SMART_CITY"),("Industrial SCADA Environment","INDUSTRIAL")]
    for name, twin_type in twins:
        twin = DigitalTwin.objects.create(
            name=name, twin_type=twin_type, organization=org, status="IDLE",
            topology={"nodes": random.randint(10,50), "edges": random.randint(20,100)},
            assets=[{"name":"Core Server","type":"server","criticality":"CRITICAL"}],
            vulnerabilities=[{"cve":f"CVE-2024-{random.randint(1000,9999)}","severity":"HIGH"}],
        )
        for _ in range(random.randint(1,3)):
            scenario = random.choice(["RANSOMWARE","DDoS","APT_LATERAL","SUPPLY_CHAIN","INSIDER"])
            sim = TwinSimulation.objects.create(twin=twin, attack_scenario=scenario, status="RUNNING")
            _execute_simulation(sim, twin)

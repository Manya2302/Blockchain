"""TAP-DEV Phase 5 — Self-Healing Blockchain Infrastructure Views"""
import json, random, time
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import InfrastructureHealth, HealingEvent

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
def infra_dashboard(request):
    _seed_infra()
    components = InfrastructureHealth.objects.order_by("health_score")
    events = HealingEvent.objects.select_related("component").order_by("-triggered_at")[:20]
    healthy = components.filter(status="HEALTHY").count()
    critical = components.filter(status__in=["CRITICAL","OFFLINE"]).count()
    avg_health = sum(c.health_score for c in components) / max(components.count(), 1)
    overall_uptime = sum(c.uptime_percent for c in components) / max(components.count(), 1)
    return render(request, "self_healing/dashboard.html", {
        "components": components, "events": events,
        "stats": {"total": components.count(), "healthy": healthy, "critical": critical,
                  "avg_health": round(avg_health, 1), "uptime": round(overall_uptime, 2)},
        "health_json": json.dumps([{"id":c.id,"component":c.component,"status":c.status,
                                    "health":c.health_score,"color":c.status_color} for c in components]),
    })

@admin_required
def trigger_heal(request, component_id):
    component = InfrastructureHealth.objects.get(id=component_id)
    old_status = component.status
    component.status = "HEALING"
    component.save()
    time.sleep(0.1)
    action = random.choice(["REROUTE","RESTORE","FAILOVER","REPIN","BACKUP_NODE"])
    healed = random.random() > 0.15
    HealingEvent.objects.create(
        component=component,
        action_type=action,
        description=f"Auto-heal: {action.replace('_',' ').title()} triggered for {component.component_id}",
        success=healed, evidence_affected=random.randint(0, 50),
        completed_at=timezone.now(), recovery_time_seconds=random.randint(5,120),
        auto_triggered=False, triggered_by=request.user,
    )
    component.status = "RECOVERED" if healed else "CRITICAL"
    component.health_score = random.uniform(85, 100) if healed else random.uniform(20, 50)
    component.auto_healed = healed
    component.save()
    messages.success(request, f"Self-heal triggered: {action}. Status: {'RECOVERED' if healed else 'STILL CRITICAL'}")
    return redirect("self_healing:dashboard")

@analyst_required
def infra_api(request):
    components = list(InfrastructureHealth.objects.values(
        "component","component_id","status","health_score","latency_ms","uptime_percent"))
    return JsonResponse({"components": components, "timestamp": timezone.now().isoformat()})

def _seed_infra():
    if InfrastructureHealth.objects.exists(): return
    components_data = [
        ("BLOCKCHAIN_NODE","ethereum-mainnet-node-01",98.5,"HEALTHY",12,0.001,99.97),
        ("BLOCKCHAIN_NODE","polygon-node-01",97.2,"HEALTHY",8,0.002,99.95),
        ("IPFS_NODE","ipfs-cluster-primary",95.0,"HEALTHY",45,0.01,99.90),
        ("IPFS_NODE","ipfs-backup-us-east",72.0,"DEGRADED",234,0.08,98.5),
        ("AI_CLUSTER","bilstm-inference-gpu-01",99.1,"HEALTHY",5,0.001,99.99),
        ("AI_CLUSTER","federated-aggregator",88.0,"HEALTHY",67,0.02,99.80),
        ("DATABASE","postgres-primary",100.0,"HEALTHY",3,0.0,100.0),
        ("DATABASE","postgres-replica-eu",45.0,"CRITICAL",1200,0.35,94.2),
        ("API_GATEWAY","cloudflare-edge-us",98.8,"HEALTHY",4,0.001,99.98),
        ("FORENSIC_NODE","interpol-node-01",87.5,"HEALTHY",156,0.05,99.1),
        ("EVIDENCE_STORE","s3-evidence-primary",99.5,"HEALTHY",22,0.001,99.99),
        ("EVIDENCE_STORE","azure-backup-eu",31.0,"OFFLINE",0,1.0,78.5),
    ]
    for comp, comp_id, health, status, latency, error_rate, uptime in components_data:
        node = InfrastructureHealth.objects.create(
            component=comp, component_id=comp_id, health_score=health,
            status=status, latency_ms=latency, error_rate=error_rate, uptime_percent=uptime,
            heal_actions=["reroute_traffic"] if status in ("DEGRADED","CRITICAL","OFFLINE") else [],
        )
        if status in ("DEGRADED","CRITICAL","OFFLINE"):
            HealingEvent.objects.create(
                component=node, action_type=random.choice(["REROUTE","RESTORE","FAILOVER"]),
                description=f"Automated recovery triggered for {comp_id}",
                success=status=="DEGRADED", evidence_affected=random.randint(5, 200),
                completed_at=timezone.now(), recovery_time_seconds=random.randint(30,600),
            )

"""TAP-DEV Phase 5 — Developer Ecosystem Views"""
import json, secrets, hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MarketplacePlugin, DeveloperApp

@login_required
def ecosystem_dashboard(request):
    _seed_plugins()
    plugins = MarketplacePlugin.objects.filter(status="APPROVED").order_by("-installs")
    my_apps = DeveloperApp.objects.filter(developer=request.user).order_by("-created_at")
    total_installs = sum(p.installs for p in plugins)
    return render(request, "developer_ecosystem/dashboard.html", {
        "plugins": plugins, "my_apps": my_apps,
        "stats": {"plugins": plugins.count(), "my_apps": my_apps.count(), "total_installs": total_installs},
        "plugin_types": MarketplacePlugin.PLUGIN_TYPE,
    })

@login_required
def create_app(request):
    if request.method == "POST":
        from apps.organizations.models import Organization
        org = Organization.objects.filter(memberships__user=request.user).first()
        client_id, secret, secret_hash = DeveloperApp.generate_credentials()
        app = DeveloperApp.objects.create(
            name=request.POST["name"], developer=request.user, organization=org,
            client_id=client_id, client_secret_hash=secret_hash,
            description=request.POST.get("description",""),
            scopes=request.POST.getlist("scopes[]") or ["evidence:read","ai:predict"],
        )
        request.session["new_client_secret"] = secret
        messages.success(request, f"App '{app.name}' created. Save client secret — shown once.")
        return redirect("developer_ecosystem:dashboard")
    return render(request, "developer_ecosystem/create_app.html", {
        "available_scopes": ["evidence:read","evidence:write","ai:predict","zkp:create","blockchain:read","iot:push","reports:download"],
    })

@login_required
def api_docs(request):
    endpoints = [
        ("GET","/api/v5/evidence/","List evidence with pagination + filters","evidence:read"),
        ("POST","/api/v5/evidence/upload/","Upload new evidence with SHA-256 hashing","evidence:write"),
        ("POST","/api/v5/ai/predict/<pk>/","Run BiLSTM AI prediction on evidence","ai:predict"),
        ("GET","/api/v5/blockchain/status/<pk>/","Get blockchain anchor status","blockchain:read"),
        ("POST","/api/v5/zkp/create/<pk>/","Generate Zero-Knowledge Proof","zkp:create"),
        ("GET","/api/v5/threats/feed/","Global threat intelligence feed","threats:read"),
        ("POST","/api/v5/iot/push/","Push IoT device data","iot:push"),
        ("GET","/api/v5/network/nodes/","Global forensic network nodes","network:read"),
        ("POST","/api/v5/investigate/","Launch autonomous AI investigation","ai:investigate"),
        ("GET","/api/v5/dao/proposals/","DAO governance proposals","dao:read"),
    ]
    sdks = [
        {"lang":"Python","version":"5.0.0","install":"pip install tapdev-sdk","badge":"🐍"},
        {"lang":"JavaScript","version":"5.0.0","install":"npm install @tapdev/sdk","badge":"⚡"},
        {"lang":"Go","version":"5.0.0","install":"go get github.com/tapdev/sdk-go","badge":"🔷"},
        {"lang":"Java","version":"5.0.0","install":"maven: com.tapdev:sdk:5.0.0","badge":"☕"},
        {"lang":"Rust","version":"5.0.0","install":"cargo add tapdev-sdk","badge":"🦀"},
        {"lang":"Flutter","version":"5.0.0","install":"tapdev: ^5.0.0","badge":"📱"},
    ]
    return render(request, "developer_ecosystem/api_docs.html", {"endpoints": endpoints, "sdks": sdks})

def _seed_plugins():
    if MarketplacePlugin.objects.filter(status="APPROVED").exists():
        return
    from django.contrib.auth.models import User
    user = User.objects.filter(is_superuser=True).first()
    if user is None:
        user = User.objects.first()
    if user is None:
        return
    plugins_data = [
        ("Splunk SIEM Connector","splunk-connector","CONNECTOR","Bidirectional sync with Splunk SIEM","1.2.0",0,4892,4.7,245,True),
        ("Maltego Integration","maltego-integration","INTEGRATION","Evidence graph export to Maltego","2.0.1",49,2341,4.5,180,True),
        ("Excel Forensic Report","excel-reporter","REPORTER","Export forensic reports to Excel format","1.0.3",0,5621,4.3,310,True),
        ("3D Evidence Visualizer","3d-visualizer","VISUALIZER","WebGL 3D forensic graph visualization","1.1.0",99,1204,4.8,94,True),
        ("ServiceNow Workflow","servicenow-workflow","WORKFLOW","Auto-create incidents in ServiceNow","1.0.0",199,789,4.6,67,True),
        ("Wireshark PCAP Analyzer","pcap-analyzer","ANALYZER","Import and analyze Wireshark captures","0.9.5",0,987,4.1,78,False),
        ("AWS CloudTrail Connector","aws-cloudtrail","CONNECTOR","Ingest AWS CloudTrail events as evidence","2.1.0",0,3456,4.9,201,True),
        ("Microsoft Sentinel","ms-sentinel","INTEGRATION","Bidirectional Microsoft Sentinel integration","1.0.0",299,1122,4.7,88,True),
    ]
    for name,slug,ptype,desc,ver,price,installs,rating,rcount,certified in plugins_data:
        MarketplacePlugin.objects.get_or_create(
            slug=slug,
            defaults=dict(
                name=name, plugin_type=ptype, description=desc, version=ver,
                author=user, status="APPROVED", price=price, installs=installs,
                rating=rating, ratings_count=rcount, is_certified=certified,
            )
        )

"""TAP-DEV Phase 4 — Executive Dashboard Views"""
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Sum

def admin_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,'profile',None),'role','') == 'ADMIN':
            return fn(request, *args, **kwargs)
        messages.error(request, 'Executive access required.'); return redirect('dashboard:home')
    return wrap

@admin_required
def executive_dashboard(request):
    """C-suite / Executive KPI dashboard."""
    from apps.evidence.models import Evidence
    from apps.ai_engine.models import AIPrediction
    from apps.blockchain.models import BlockchainTransaction
    from apps.organizations.models import Organization, OrganizationMembership
    from apps.soc.models import SOCAlert
    from apps.billing.models import OrganizationSubscription
    from apps.users.models import ActivityLog
    from apps.iot_gateway.models import IoTDevice, IoTDataPush
    from apps.threat_intel.models import ThreatPrediction
    from apps.compliance.models import ComplianceAssessment
    from apps.zkp.models import ZKPVerification

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month  = (month_start - timezone.timedelta(days=1)).replace(day=1)

    # Platform-wide KPIs
    kpis = {
        'total_orgs':          Organization.objects.count(),
        'active_subs':         OrganizationSubscription.objects.filter(status='ACTIVE').count(),
        'total_evidence':      Evidence.objects.count(),
        'total_users':         OrganizationMembership.objects.filter(is_active=True).count(),
        'ai_scans_total':      AIPrediction.objects.count(),
        'blockchain_total':    BlockchainTransaction.objects.count(),
        'threats_detected':    ThreatPrediction.objects.filter(risk_level__in=['CRITICAL','HIGH']).count(),
        'fraud_prevented':     AIPrediction.objects.filter(risk_level__in=['HIGH','CRITICAL']).count(),
        'iot_devices':         IoTDevice.objects.filter(status='ACTIVE').count(),
        'iot_pushes':          IoTDataPush.objects.count(),
        'zkp_proofs':          ZKPVerification.objects.filter(status='VALID').count(),
        'compliance_passed':   ComplianceAssessment.objects.filter(status='COMPLETED', overall_score__gte=80).count(),
        'open_soc_alerts':     SOCAlert.objects.filter(status='OPEN').count(),
        'critical_alerts':     SOCAlert.objects.filter(status='OPEN', severity='CRITICAL').count(),
        'avg_trust_score':     round(Evidence.objects.aggregate(a=Avg('trust_score'))['a'] or 0, 1),
        'monthly_revenue':     _calc_monthly_revenue(),
        'fraud_value_saved':   AIPrediction.objects.filter(risk_level__in=['HIGH','CRITICAL']).count() * 15000,
    }

    # Monthly evidence growth (last 6 months)
    growth_labels, growth_vals = [], []
    for i in range(5, -1, -1):
        dt = now - timezone.timedelta(days=30*i)
        ms = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        me = (ms + timezone.timedelta(days=32)).replace(day=1)
        c  = Evidence.objects.filter(created_at__range=(ms, me)).count()
        growth_labels.append(dt.strftime('%b %Y'))
        growth_vals.append(c)

    # Risk distribution
    risk_dist = {
        lvl: AIPrediction.objects.filter(risk_level=lvl).count()
        for lvl in ['SAFE','LOW','MEDIUM','HIGH','CRITICAL']
    }

    # Organization health heatmap data
    orgs = Organization.objects.filter(status__in=['ACTIVE','TRIAL']).annotate(
        ev_count=Count('memberships__user__submitted_evidence', distinct=True)
    )[:20]
    org_health = []
    for org in orgs:
        alerts = SOCAlert.objects.filter(organization=org, status='OPEN').count()
        org_health.append({
            'name': org.name[:20], 'type': org.org_type,
            'alerts': alerts, 'members': org.member_count,
            'status': org.status,
            'risk': 'high' if alerts > 5 else ('medium' if alerts > 2 else 'low'),
        })

    # Industry breakdown
    industry_data = (
        Organization.objects.values('org_type').annotate(c=Count('id')).order_by('-c')[:8]
    )
    industry_labels = [d['org_type'].replace('_',' ').title() for d in industry_data]
    industry_vals   = [d['c'] for d in industry_data]

    return render(request, 'executive/dashboard.html', {
        'kpis': kpis,
        'growth_labels_json': json.dumps(growth_labels),
        'growth_vals_json':   json.dumps(growth_vals),
        'risk_dist_json':     json.dumps(risk_dist),
        'org_health':         org_health,
        'org_health_json':    json.dumps(org_health),
        'industry_labels_json': json.dumps(industry_labels),
        'industry_vals_json':   json.dumps(industry_vals),
    })

def _calc_monthly_revenue():
    try:
        from apps.billing.models import OrganizationSubscription
        subs = OrganizationSubscription.objects.filter(status='ACTIVE').select_related('plan')
        return round(sum(float(s.plan.price_month) for s in subs), 2)
    except Exception:
        return 0.0

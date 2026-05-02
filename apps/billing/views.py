"""TAP-DEV Phase 4 — Billing & Subscription Views"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import SubscriptionPlan, OrganizationSubscription, UsageEvent

def admin_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,'profile',None),'role','') == 'ADMIN':
            return fn(request, *args, **kwargs)
        messages.error(request, 'Admin access required.'); return redirect('dashboard:home')
    return wrap

@login_required
def billing_dashboard(request):
    _seed_plans()
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_month')
    from apps.organizations.models import Organization, OrganizationMembership
    membership = OrganizationMembership.objects.filter(user=request.user, is_active=True).first()
    org = membership.organization if membership else None
    subscription = None
    usage_events = []
    if org:
        try:
            subscription = org.subscription
        except Exception:
            pass
        usage_events = UsageEvent.objects.filter(organization=org).order_by('-timestamp')[:20]

    usage_chart = _build_usage_chart(org)
    return render(request, 'billing/dashboard.html', {
        'plans': plans, 'org': org, 'subscription': subscription,
        'usage_events': usage_events, 'usage_chart_json': json.dumps(usage_chart),
    })

@admin_required
def admin_billing(request):
    """Super-admin billing overview across all organizations."""
    _seed_plans()
    from apps.organizations.models import Organization
    orgs = Organization.objects.prefetch_related('subscription').order_by('-created_at')
    plans = SubscriptionPlan.objects.filter(is_active=True)
    subs_all = OrganizationSubscription.objects.select_related('organization','plan').order_by('-started_at')
    monthly_revenue = sum(
        float(s.plan.price_month) for s in subs_all if s.status == 'ACTIVE'
    )
    subs = subs_all
    return render(request, 'billing/admin.html', {
        'orgs': orgs, 'subs': subs, 'plans': plans,
        'monthly_revenue': monthly_revenue,
        'total_orgs': orgs.count(),
        'active_subs': subs.filter(status='ACTIVE').count(),
        'trial_subs': subs.filter(status='TRIALING').count(),
    })

@admin_required
def change_plan(request, org_id):
    from apps.organizations.models import Organization
    org = get_object_or_404(Organization, id=org_id)
    if request.method == 'POST':
        plan_name = request.POST.get('plan')
        plan = get_object_or_404(SubscriptionPlan, name=plan_name)
        sub, _ = OrganizationSubscription.objects.get_or_create(
            organization=org, defaults={'plan': plan, 'status': 'ACTIVE'}
        )
        sub.plan = plan
        sub.status = 'ACTIVE'
        sub.current_period_end = timezone.now() + timezone.timedelta(days=30)
        sub.save()
        org.max_users       = plan.max_users
        org.max_evidence_gb = plan.max_evidence_gb
        org.api_quota_daily = plan.api_calls_day
        org.save()
        messages.success(request, f"{org.name} upgraded to {plan.name} plan.")
    return redirect('billing:admin')

def _build_usage_chart(org):
    if not org: return {}
    from django.db.models.functions import TruncDay
    from django.db.models import Count, Sum
    last_7 = timezone.now() - timezone.timedelta(days=7)
    events = (
        UsageEvent.objects.filter(organization=org, timestamp__gte=last_7)
        .annotate(day=TruncDay('timestamp'))
        .values('day','event_type').annotate(c=Count('id')).order_by('day')
    )
    result = {}
    for e in events:
        day_str = e['day'].strftime('%b %d') if e['day'] else ''
        if day_str not in result: result[day_str] = {}
        result[day_str][e['event_type']] = e['c']
    return result

def _seed_plans():
    plans_data = [
        ('FREE', 0, 0, 5, 1.0, 100, 50, 10, ['SHA-256 Hashing','Basic Event Chain','PDF Reports']),
        ('STARTER', 49, 490, 15, 10.0, 1000, 500, 50,
         ['Everything in Free','AI Anomaly Detection','Blockchain Anchoring','API Access']),
        ('PROFESSIONAL', 199, 1990, 50, 50.0, 10000, 2000, 500,
         ['Everything in Starter','Forensic Graph','Evolution Tracker','ZKP Verification','SOC Dashboard','Attack Simulator']),
        ('ENTERPRISE', 999, 9990, 500, 500.0, 100000, 20000, 5000,
         ['Everything in Professional','Multi-Tenant SaaS','IoT Gateway','Federated AI','Compliance Suite','Priority Support']),
        ('GOVERNMENT', 2499, 24990, 9999, 9999.0, 999999, 99999, 99999,
         ['Everything in Enterprise','Air-Gap Deployment','FIPS 140-2','Custom SLAs','Dedicated Infrastructure']),
    ]
    for name, pm, py, mu, gb, api, ai, bc, feats in plans_data:
        SubscriptionPlan.objects.get_or_create(name=name, defaults={
            'price_month': pm, 'price_year': py, 'max_users': mu,
            'max_evidence_gb': gb, 'api_calls_day': api,
            'ai_scans_month': ai, 'blockchain_anchors': bc, 'features': feats,
        })

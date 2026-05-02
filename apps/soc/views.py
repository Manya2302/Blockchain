"""TAP-DEV Phase 4 — SOC Dashboard Views"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg
from .models import SOCAlert, LiveFeed


def analyst_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        role = getattr(getattr(request.user,'profile',None),'role','SUBMITTER')
        if role in ('ANALYST','ADMIN'):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Analyst or Admin access required.')
        return redirect('dashboard:home')
    return wrapper


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        role = getattr(getattr(request.user,'profile',None),'role','SUBMITTER')
        if role == 'ADMIN':
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    return wrapper


@analyst_required
def soc_dashboard(request):
    """Main Security Operations Center dashboard."""
    from apps.ai_engine.models import AIPrediction
    from apps.evidence.models import Evidence
    from apps.blockchain.models import BlockchainTransaction
    from apps.users.models import ActivityLog

    # Active alerts
    open_alerts_qs = SOCAlert.objects.filter(status='OPEN').order_by('-detected_at')
    critical_count = open_alerts_qs.filter(severity='CRITICAL').count()
    high_count     = open_alerts_qs.filter(severity='HIGH').count()
    alerts = open_alerts_qs[:50]

    # Live feed (last 30 events)
    feed = LiveFeed.objects.order_by('-timestamp')[:30]

    # Real-time stats
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stats = {
        'evidence_today':   Evidence.objects.filter(created_at__gte=today_start).count(),
        'ai_scans_today':   AIPrediction.objects.filter(predicted_at__gte=today_start).count(),
        'blockchain_today': BlockchainTransaction.objects.filter(anchored_at__gte=today_start).count(),
        'open_alerts':      SOCAlert.objects.filter(status='OPEN').count(),
        'critical_alerts':  critical_count,
        'high_alerts':      high_count,
        'logins_today':     ActivityLog.objects.filter(action='LOGIN', timestamp__gte=today_start).count(),
    }

    # Severity chart data
    severity_data = {
        s: SOCAlert.objects.filter(severity=s, status='OPEN').count()
        for s in ['CRITICAL','HIGH','MEDIUM','LOW','INFO']
    }

    # Alert type breakdown
    alert_types = (
        SOCAlert.objects.filter(status='OPEN')
        .values('alert_type').annotate(c=Count('id')).order_by('-c')[:8]
    )

    # Geo data for threat map
    geo_alerts = SOCAlert.objects.filter(
        geo_lat__isnull=False, status='OPEN'
    ).values('geo_lat','geo_lon','severity','title','geo_country')[:100]

    # 24-hour alert trend
    from django.db.models.functions import TruncHour
    hourly_trend = (
        SOCAlert.objects.filter(detected_at__gte=now - timezone.timedelta(hours=24))
        .annotate(hour=TruncHour('detected_at'))
        .values('hour').annotate(count=Count('id')).order_by('hour')
    )
    trend_labels = [h['hour'].strftime('%H:00') if h['hour'] else '' for h in hourly_trend]
    trend_values = [h['count'] for h in hourly_trend]

    # Recent AI predictions with HIGH/CRITICAL risk
    recent_threats = AIPrediction.objects.filter(
        risk_level__in=['HIGH','CRITICAL']
    ).select_related('evidence').order_by('-predicted_at')[:10]

    return render(request, 'soc/dashboard.html', {
        'alerts': alerts[:20],
        'feed': feed,
        'stats': stats,
        'severity_data_json': json.dumps(severity_data),
        'alert_types': alert_types,
        'geo_alerts_json': json.dumps(list(geo_alerts)),
        'trend_labels_json': json.dumps(trend_labels),
        'trend_values_json': json.dumps(trend_values),
        'recent_threats': recent_threats,
    })


@analyst_required
def alert_detail(request, alert_id):
    """Individual alert investigation view."""
    alert = get_object_or_404(SOCAlert, id=alert_id)
    return render(request, 'soc/alert_detail.html', {'alert': alert})


@analyst_required
def resolve_alert(request, alert_id):
    """Mark an alert as resolved or false positive."""
    alert = get_object_or_404(SOCAlert, id=alert_id)
    if request.method == 'POST':
        resolution = request.POST.get('resolution', 'RESOLVED')
        alert.status = resolution
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()
        messages.success(request, f'Alert marked as {resolution}.')
    return redirect('soc:dashboard')


@analyst_required
def live_feed_api(request):
    """JSON API for real-time feed updates (polling)."""
    since = request.GET.get('since', '')
    feed_qs = LiveFeed.objects.order_by('-timestamp')[:20]
    data = [{
        'id': f.id, 'type': f.feed_type, 'message': f.message,
        'icon': f.icon, 'color': f.color,
        'timestamp': f.timestamp.isoformat(),
        'user': f.user.username if f.user else 'System',
    } for f in feed_qs]
    return JsonResponse({'feed': data, 'count': len(data)})


@analyst_required
def soc_stats_api(request):
    """Live stats for SOC dashboard widgets."""
    from apps.evidence.models import Evidence
    from apps.ai_engine.models import AIPrediction
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return JsonResponse({
        'evidence_today': Evidence.objects.filter(created_at__gte=today).count(),
        'open_alerts':    SOCAlert.objects.filter(status='OPEN').count(),
        'critical':       SOCAlert.objects.filter(status='OPEN', severity='CRITICAL').count(),
        'ai_scans':       AIPrediction.objects.filter(predicted_at__gte=today).count(),
        'timestamp':      now.isoformat(),
    })


def create_soc_alert(alert_type, title, description, severity='MEDIUM', evidence=None,
                     user=None, source_ip=None, geo_data=None, ai_confidence=0.0, org=None):
    """Helper to create SOC alerts from any app."""
    geo = geo_data or {}
    alert = SOCAlert.objects.create(
        alert_type=alert_type, title=title, description=description,
        severity=severity, evidence=evidence, triggered_by_user=user,
        source_ip=source_ip, geo_country=geo.get('country',''),
        geo_city=geo.get('city',''), geo_lat=geo.get('lat'),
        geo_lon=geo.get('lon'), ai_confidence=ai_confidence,
        organization=org,
    )
    # Add to live feed
    icons = {'CRITICAL':'🔴','HIGH':'🟠','MEDIUM':'🟡','LOW':'🟢','INFO':'🔵'}
    LiveFeed.objects.create(
        feed_type='ALERT', message=f"[{severity}] {title}",
        icon=icons.get(severity,'⚠'), color=alert.severity_color,
        user=user, organization=org,
    )
    return alert

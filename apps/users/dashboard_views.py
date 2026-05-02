"""TAP-DEV Phase 2 — Dashboard Views with analytics"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
import json
from .models import UserProfile, ActivityLog
from .forms import UserEditForm
from .utils import log_activity


def require_role(*roles):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, 'profile') or request.user.profile.role not in roles:
                messages.error(request, 'Access denied.')
                return redirect('dashboard:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
def home(request):
    role = getattr(getattr(request.user, 'profile', None), 'role', 'SUBMITTER')
    if role == 'ADMIN':    return redirect('dashboard:admin')
    elif role == 'ANALYST': return analyst_dash(request)
    else:                   return submitter_dash(request)


@login_required
def submitter_dash(request):
    from apps.evidence.models import Evidence
    from apps.events.models import Event
    from apps.analysis.models import Anomaly
    evidences     = Evidence.objects.filter(uploader=request.user).order_by('-created_at')
    recent_events = Event.objects.filter(evidence__uploader=request.user).order_by('-timestamp')[:8]
    # Last 7 days upload trend
    today = timezone.now().date()
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        cnt = evidences.filter(created_at__date=day).count()
        trend.append({'day': day.strftime('%a'), 'count': cnt})
    stats = {
        'total':    evidences.count(),
        'verified': evidences.filter(status='VERIFIED').count(),
        'pending':  evidences.filter(status='PENDING').count(),
        'flagged':  evidences.filter(status='FLAGGED').count(),
        'stored':   evidences.filter(status='STORED').count(),
        'avg_trust':evidences.aggregate(a=Avg('trust_score'))['a'] or 100,
        'open_anomalies': Anomaly.objects.filter(evidence__uploader=request.user, is_resolved=False).count(),
    }
    return render(request, 'dashboard/submitter.html', {
        'evidences': evidences[:6], 'recent_events': recent_events,
        'stats': stats, 'trend_json': json.dumps(trend),
    })


@login_required
def analyst_dash(request):
    from apps.evidence.models import Evidence
    from apps.analysis.models import Anomaly
    from apps.events.models import Event
    evidences  = Evidence.objects.select_related('uploader').order_by('-created_at')
    anomalies  = Anomaly.objects.filter(is_resolved=False).select_related('evidence').order_by('-detected_at')[:12]
    # Anomaly severity breakdown
    sev_data = list(Anomaly.objects.filter(is_resolved=False).values('severity').annotate(c=Count('id')))
    # Trust distribution
    trust_ranges = [
        {'label':'100','count': evidences.filter(trust_score=100).count()},
        {'label':'80–99','count': evidences.filter(trust_score__gte=80,trust_score__lt=100).count()},
        {'label':'50–79','count': evidences.filter(trust_score__gte=50,trust_score__lt=80).count()},
        {'label':'<50','count': evidences.filter(trust_score__lt=50).count()},
    ]
    # Timeline: events per day last 14 days
    today = timezone.now().date()
    event_trend = []
    for i in range(13,-1,-1):
        day = today - timedelta(days=i)
        cnt = Event.objects.filter(timestamp__date=day).count()
        event_trend.append({'day': day.strftime('%m/%d'), 'count': cnt})
    stats = {
        'total':     evidences.count(),
        'verified':  evidences.filter(status='VERIFIED').count(),
        'flagged':   evidences.filter(status='FLAGGED').count(),
        'stored':    evidences.filter(status='STORED').count(),
        'anomalies': Anomaly.objects.filter(is_resolved=False).count(),
        'high_risk': evidences.filter(trust_score__lt=50).count(),
        'avg_trust': evidences.aggregate(a=Avg('trust_score'))['a'] or 100,
        'total_events': Event.objects.count(),
    }
    return render(request, 'dashboard/analyst.html', {
        'evidences': evidences[:8], 'anomalies': anomalies, 'stats': stats,
        'sev_json': json.dumps(sev_data),
        'trust_json': json.dumps(trust_ranges),
        'event_trend_json': json.dumps(event_trend),
    })


@require_role('ADMIN')
def admin_dash(request):
    from apps.evidence.models import Evidence
    from apps.analysis.models import Anomaly
    from apps.events.models import Event
    users      = User.objects.select_related('profile').all()
    evidences  = Evidence.objects.select_related('uploader').all()
    activities = ActivityLog.objects.select_related('user').order_by('-timestamp')[:20]
    # User growth per day (last 7 days)
    today = timezone.now().date()
    user_trend = []
    for i in range(6,-1,-1):
        day = today - timedelta(days=i)
        cnt = users.filter(date_joined__date=day).count()
        user_trend.append({'day': day.strftime('%a'), 'count': cnt})
    # Category breakdown of activities
    cat_data = list(ActivityLog.objects.values('category').annotate(c=Count('id')))
    stats = {
        'users':      users.count(),
        'evidences':  evidences.count(),
        'anomalies':  Anomaly.objects.filter(is_resolved=False).count(),
        'activities': ActivityLog.objects.count(),
        'submitters': users.filter(profile__role='SUBMITTER').count(),
        'analysts':   users.filter(profile__role='ANALYST').count(),
        'admins':     users.filter(profile__role='ADMIN').count(),
        'high_risk':  evidences.filter(trust_score__lt=50).count(),
        'events':     Event.objects.count(),
        'avg_trust':  evidences.aggregate(a=Avg('trust_score'))['a'] or 100,
    }
    return render(request, 'dashboard/admin.html', {
        'users': users[:8], 'evidences': evidences[:6],
        'activities': activities, 'stats': stats,
        'user_trend_json': json.dumps(user_trend),
        'cat_data_json': json.dumps(cat_data),
    })


@require_role('ADMIN')
def user_list(request):
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    search = request.GET.get('q','')
    role   = request.GET.get('role','')
    if search: users = users.filter(Q(username__icontains=search)|Q(email__icontains=search))
    if role:   users = users.filter(profile__role=role)
    return render(request, 'dashboard/user_list.html', {
        'users': users, 'search': search, 'role': role,
        'roles': UserProfile.ROLE_CHOICES,
    })


@require_role('ADMIN')
def user_edit(request, uid):
    target = get_object_or_404(User, pk=uid)
    form = UserEditForm(request.POST or None, instance=target,
        initial={'role': target.profile.role, 'department': target.profile.department})
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.profile.role = form.cleaned_data['role']
        user.profile.department = form.cleaned_data.get('department','')
        user.profile.save()
        log_activity(request.user, 'USER_EDIT', 'ADMIN', f"Edited user {user.username}", request=request)
        messages.success(request, f'User {user.username} updated.')
        return redirect('dashboard:user_list')
    return render(request, 'dashboard/user_edit.html', {'form': form, 'target': target})


@require_role('ADMIN')
def user_delete(request, uid):
    target = get_object_or_404(User, pk=uid)
    if request.method == 'POST':
        uname = target.username
        target.delete()
        log_activity(request.user, 'USER_DELETE', 'ADMIN', f"Deleted user {uname}", request=request)
        messages.success(request, f'User {uname} deleted.')
        return redirect('dashboard:user_list')
    return render(request, 'dashboard/user_confirm_delete.html', {'target': target})

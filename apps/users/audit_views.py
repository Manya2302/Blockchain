"""TAP-DEV Phase 2 — Audit Log Views"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ActivityLog


@login_required
def audit_view(request):
    category = request.GET.get('category','')
    search   = request.GET.get('q','')
    if request.user.profile.is_admin:
        qs = ActivityLog.objects.select_related('user').all()
    else:
        qs = ActivityLog.objects.filter(user=request.user)
    if category: qs = qs.filter(category=category)
    if search:   qs = qs.filter(action__icontains=search)
    return render(request, 'audit/logs.html', {
        'logs': qs[:200], 'category': category, 'search': search,
        'categories': ActivityLog.CATEGORY_CHOICES,
    })

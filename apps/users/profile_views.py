"""TAP-DEV Phase 2 — Profile Views"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProfileForm
from .utils import log_activity


@login_required
def profile_view(request):
    from apps.evidence.models import Evidence
    from apps.events.models import Event
    from .models import ActivityLog
    evidences = Evidence.objects.filter(uploader=request.user).order_by('-created_at')[:5]
    recent_logs = ActivityLog.objects.filter(user=request.user).order_by('-timestamp')[:10]
    return render(request, 'profile/view.html', {
        'evidences': evidences,
        'recent_logs': recent_logs,
        'ev_count': Evidence.objects.filter(uploader=request.user).count(),
        'event_count': Event.objects.filter(actor=request.user).count(),
    })


@login_required
def profile_edit(request):
    profile = request.user.profile
    initial = {'first_name': request.user.first_name, 'last_name': request.user.last_name, 'email': request.user.email}
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile, initial=initial)
    if request.method == 'POST' and form.is_valid():
        # Update User fields
        request.user.first_name = form.cleaned_data.get('first_name','')
        request.user.last_name  = form.cleaned_data.get('last_name','')
        request.user.email      = form.cleaned_data.get('email','')
        request.user.save()
        form.save()
        log_activity(request.user, 'PROFILE_UPDATE', 'PROFILE', request=request)
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile:view')
    return render(request, 'profile/edit.html', {'form': form})

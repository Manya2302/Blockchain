"""TAP-DEV Phase 2 — Report Views"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib import messages
from apps.evidence.models import Evidence
from apps.users.utils import log_activity
from .generator import generate_evidence_report


@login_required
def download_report(request, pk):
    ev = get_object_or_404(Evidence, pk=pk)
    if not hasattr(request.user,'profile') or (
        request.user.profile.role == 'SUBMITTER' and ev.uploader != request.user):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    events   = list(ev.events.order_by('sequence_number'))
    anomalies = list(ev.anomalies.order_by('-detected_at'))

    buffer, error = generate_evidence_report(ev, events, anomalies, request.user)
    if error:
        messages.error(request, f'Report error: {error}')
        return redirect('evidence:detail', pk=pk)

    log_activity(request.user, 'REPORT_DOWNLOAD', 'REPORT', f"Evidence #{pk}: {ev.title}", request=request)

    filename = f"tapdev_report_{ev.id}_{ev.sha256_hash[:8]}.pdf"
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

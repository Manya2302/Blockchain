from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.evidence.models import Evidence
from .models import Anomaly
from .detector import AnomalyDetector
from .scoring import TrustScorer

def require_analyst(fn):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user,'profile') or request.user.profile.role not in ('ANALYST','ADMIN'):
            messages.error(request,'Analyst access required.')
            return redirect('dashboard:home')
        return fn(request, *args, **kwargs)
    return wrapper

@require_analyst
def anomaly_list(request):
    severity = request.GET.get('severity','')
    qs = Anomaly.objects.select_related('evidence','related_event').filter(is_resolved=False)
    if severity: qs = qs.filter(severity=severity)
    return render(request,'analysis/anomaly_list.html',{'anomalies':qs,'severity':severity})

@require_analyst
def resolve_anomaly(request, pk):
    a = get_object_or_404(Anomaly, pk=pk)
    if request.method == 'POST':
        a.is_resolved = True; a.resolved_by = request.user
        a.resolved_at = timezone.now(); a.notes = request.POST.get('notes','')
        a.save(); TrustScorer(a.evidence).recalculate()
        messages.success(request,'Anomaly resolved. Trust score updated.')
    return redirect(request.META.get('HTTP_REFERER','analysis:anomaly_list'))

@require_analyst
def rescan_evidence(request, pk):
    ev = get_object_or_404(Evidence, pk=pk)
    AnomalyDetector(ev).run(); TrustScorer(ev).recalculate()
    messages.success(request,f'Scan complete for "{ev.title}". Trust score: {ev.trust_score}')
    return redirect('evidence:detail', pk=pk)

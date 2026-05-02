"""TAP-DEV Phase 4 — IoT Gateway Views"""
import json, hashlib
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import IoTDevice, IoTDataPush
from apps.users.security import rate_limit, validate_replay_nonce, verify_hmac_signature

def admin_required(fn):
    @login_required
    def wrap(request, *args, **kwargs):
        if getattr(getattr(request.user,'profile',None),'role','') in ('ANALYST','ADMIN'):
            return fn(request, *args, **kwargs)
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    return wrap

@admin_required
def iot_dashboard(request):
    devices   = IoTDevice.objects.select_related('organization').order_by('-registered_at')
    pushes    = IoTDataPush.objects.select_related('device').order_by('-received_at')[:40]
    active    = devices.filter(status='ACTIVE').count()
    alert_ct  = devices.filter(status='ALERT').count()
    total_pushes = IoTDataPush.objects.count()
    anomalous = IoTDataPush.objects.filter(verdict='ANOMALOUS').count()
    return render(request, 'iot_gateway/dashboard.html', {
        'devices': devices, 'pushes': pushes,
        'stats': {'total': devices.count(), 'active': active, 'alert': alert_ct,
                  'total_pushes': total_pushes, 'anomalous': anomalous},
    })

@admin_required
def register_device(request):
    if request.method == 'POST':
        from apps.organizations.models import Organization
        org_id = request.POST.get('organization')
        org = Organization.objects.filter(id=org_id).first()
        token = IoTDevice.generate_token()
        device = IoTDevice.objects.create(
            organization=org, name=request.POST['name'],
            device_type=request.POST['device_type'],
            serial_number=request.POST.get('serial_number', token[:16]),
            location=request.POST.get('location',''),
            api_token=token, registered_by=request.user,
        )
        messages.success(request, f"Device '{device.name}' registered. Token: {token}")
        request.session['new_device_token'] = token
        return redirect('iot:dashboard')
    from apps.organizations.models import Organization
    return render(request, 'iot_gateway/register.html', {
        'device_types': IoTDevice.DEVICE_TYPE,
        'orgs': Organization.objects.filter(status='ACTIVE'),
    })

@csrf_exempt
@require_POST
def device_push(request):
    """IoT device data ingestion endpoint (token-auth, no CSRF)."""
    token = request.headers.get('X-Device-Token') or request.POST.get('token','')
    device = IoTDevice.objects.filter(api_token=token, status='ACTIVE').first()
    if not device:
        return JsonResponse({'error': 'Invalid device token'}, status=401)
    if not rate_limit(request, 'iot_push', limit=120, window=60, identity=str(device.id)):
        return JsonResponse({'error': 'Rate limit exceeded'}, status=429)

    body = request.body
    max_bytes = settings.TAPDEV_CONFIG.get('IOT_MAX_PAYLOAD_KB', 512) * 1024
    if len(body) > max_bytes:
        return JsonResponse({'error': 'Payload too large'}, status=413)
    content_type = request.headers.get('Content-Type', '')
    if content_type and 'application/json' not in content_type and 'application/x-www-form-urlencoded' not in content_type:
        return JsonResponse({'error': 'Unsupported content type'}, status=415)
    nonce = request.headers.get('X-Device-Nonce', '')
    signature = request.headers.get('X-Device-Signature', '')
    require_signature = not settings.DEBUG
    if nonce or signature or require_signature:
        if not validate_replay_nonce(f'iot:{device.id}', nonce, window=300):
            return JsonResponse({'error': 'Invalid or replayed nonce'}, status=401)
        if not verify_hmac_signature(device.api_token, body + nonce.encode('utf-8'), signature):
            return JsonResponse({'error': 'Invalid device signature'}, status=401)
    payload_hash = hashlib.sha256(body).hexdigest()
    raw_preview  = body[:500].decode('utf-8', errors='replace')

    push = IoTDataPush.objects.create(
        device=device, payload_hash=payload_hash,
        payload_size=len(body), raw_preview=raw_preview, verdict='PENDING',
    )
    device.last_ping = timezone.now()
    device.total_pushes += 1
    device.save(update_fields=['last_ping','total_pushes'])

    # Quick AI score
    try:
        data = json.loads(body)
        ai_score = _score_iot_payload(data)
        push.ai_score = ai_score
        push.verdict = 'ANOMALOUS' if ai_score > 0.6 else ('SUSPICIOUS' if ai_score > 0.3 else 'CLEAN')
        push.save(update_fields=['ai_score','verdict'])
        if push.verdict == 'ANOMALOUS':
            from apps.soc.views import create_soc_alert
            create_soc_alert('IOT_INTRUSION', f"IoT Anomaly: {device.name}",
                f"Device {device.name} ({device.device_type}) pushed anomalous payload. Score: {ai_score:.2f}",
                severity='HIGH', ai_confidence=ai_score, org=device.organization)
    except Exception:
        pass

    return JsonResponse({'status': 'received', 'push_id': push.id, 'verdict': push.verdict})

def _score_iot_payload(data):
    score = 0.0
    if isinstance(data, dict):
        if data.get('error_count', 0) > 10: score += 0.3
        if data.get('anomaly_flag'): score += 0.4
        if data.get('duplicate'): score += 0.2
        ts = data.get('timestamp')
        if ts:
            import time
            try:
                drift = abs(time.time() - float(ts))
                if drift > 86400: score += 0.3
            except Exception: pass
    return min(score, 1.0)

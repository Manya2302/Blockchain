"""Shared utilities: logging, IP extraction, email sending."""
from django.core.mail import send_mail
from django.conf import settings

def get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0] if x else request.META.get('REMOTE_ADDR')

def log_activity(user, action, category='SYSTEM', detail='', request=None, metadata=None):
    from .models import ActivityLog
    ip = get_client_ip(request) if request else None
    ActivityLog.objects.create(
        user=user, action=action, category=category,
        detail=detail, ip_address=ip, metadata=metadata or {}
    )

def send_otp_email(user, otp):
    subject = 'TAP-DEV — Your Verification Code'
    body = f"""
TAP-DEV Security Verification

Your one-time code: {otp.token}

This code expires in 15 minutes. Do not share it.

If you did not request this, ignore this email.

— TAP-DEV Security System
    """.strip()
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception:
        pass  # Console backend will print it

"""
TAP-DEV Phase 2 — Users App Models
Extends auth with roles, OTP, profile images, version tracking.
"""
import hashlib, random, string
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


def profile_image_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1]
    return f"profiles/{instance.user.id}/avatar.{ext}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('SUBMITTER', 'Submitter'),
        ('ANALYST',   'Analyst'),
        ('ADMIN',     'Admin'),
    ]
    THEME_CHOICES = [('dark','Dark'),('light','Light'),('auto','Auto')]

    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role            = models.CharField(max_length=20, choices=ROLE_CHOICES, default='SUBMITTER')
    department      = models.CharField(max_length=100, blank=True)
    organization    = models.CharField(max_length=150, blank=True)
    phone           = models.CharField(max_length=30, blank=True)
    bio             = models.TextField(blank=True)
    profile_image   = models.ImageField(upload_to=profile_image_path, null=True, blank=True)
    theme           = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    is_approved     = models.BooleanField(default=True)
    two_fa_enabled  = models.BooleanField(default=False)
    email_notifs    = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    last_seen       = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tap_user_profiles'

    def __str__(self): return f"{self.user.username} [{self.role}]"

    @property
    def is_submitter(self): return self.role == 'SUBMITTER'
    @property
    def is_analyst(self): return self.role in ('ANALYST', 'ADMIN')
    @property
    def is_admin(self): return self.role == 'ADMIN'

    def get_role_class(self):
        return {'SUBMITTER':'role-submitter','ANALYST':'role-analyst','ADMIN':'role-admin'}.get(self.role,'')

    def get_avatar_initials(self):
        fn = self.user.first_name[:1] if self.user.first_name else ''
        ln = self.user.last_name[:1]  if self.user.last_name  else ''
        return (fn + ln).upper() or self.user.username[:2].upper()


class OTPToken(models.Model):
    """One-Time Password for email verification and password reset."""
    PURPOSE_CHOICES = [('PASSWORD_RESET','Password Reset'),('EMAIL_VERIFY','Email Verify')]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_tokens')
    token      = models.CharField(max_length=6)
    purpose    = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used    = models.BooleanField(default=False)

    class Meta:
        db_table = 'tap_otp_tokens'
        ordering = ['-created_at']

    @staticmethod
    def generate_for(user, purpose, expiry_minutes=15):
        OTPToken.objects.filter(user=user, purpose=purpose, is_used=False).delete()
        token = ''.join(random.choices(string.digits, k=6))
        return OTPToken.objects.create(
            user=user, token=token, purpose=purpose,
            expires_at=timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        )

    def is_valid(self): return not self.is_used and self.expires_at > timezone.now()


class ActivityLog(models.Model):
    """Full audit trail of system actions."""
    CATEGORY_CHOICES = [
        ('AUTH',      'Authentication'),
        ('EVIDENCE',  'Evidence'),
        ('ADMIN',     'Admin'),
        ('PROFILE',   'Profile'),
        ('REPORT',    'Report'),
        ('BLOCKCHAIN','Blockchain'),
        ('SYSTEM',    'System'),
    ]
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activity_logs')
    action     = models.CharField(max_length=100)
    category   = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='SYSTEM')
    detail     = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp  = models.DateTimeField(auto_now_add=True)
    metadata   = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tap_activity_logs'
        ordering = ['-timestamp']

    def __str__(self): return f"{self.user} — {self.action} @ {self.timestamp:%Y-%m-%d %H:%M}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created: UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'): instance.profile.save()

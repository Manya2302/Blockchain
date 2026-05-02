"""TAP-DEV Phase 2 — Notifications Model"""
from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    TYPE_CHOICES = [
        ('SUCCESS','Success'),('WARNING','Warning'),
        ('ERROR','Error'),('INFO','Info'),('ALERT','Alert'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    notif_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='INFO')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link       = models.CharField(max_length=255, blank=True)
    icon       = models.CharField(max_length=10, blank=True)

    class Meta:
        db_table = 'tap_notifications'
        ordering = ['-created_at']

    def get_icon(self):
        icons = {'SUCCESS':'✓','WARNING':'⚠','ERROR':'✕','INFO':'◈','ALERT':'⬟'}
        return self.icon or icons.get(self.notif_type,'◈')

    def get_type_class(self):
        return {'SUCCESS':'notif-success','WARNING':'notif-warning',
                'ERROR':'notif-error','INFO':'notif-info','ALERT':'notif-alert'}.get(self.notif_type,'notif-info')

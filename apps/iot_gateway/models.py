"""TAP-DEV Phase 4 — IoT Device Gateway Models"""
import uuid, secrets
from django.db import models
from django.contrib.auth.models import User


class IoTDevice(models.Model):
    DEVICE_TYPE = [
        ('CCTV','CCTV Camera'),('SENSOR','Smart Sensor'),('BIOMETRIC','Biometric System'),
        ('ACCESS_CTRL','Access Control'),('INDUSTRIAL','Industrial IoT'),('NETWORK','Network Device'),
        ('MOBILE_UNIT','Mobile Unit'),('DRONE','Drone / UAV'),('WEARABLE','Wearable Device'),
    ]
    STATUS_CHOICES = [('ACTIVE','Active'),('INACTIVE','Inactive'),('ALERT','In Alert'),('MAINTENANCE','Maintenance')]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('tap_org.Organization', on_delete=models.CASCADE, related_name='iot_devices')
    name         = models.CharField(max_length=150)
    device_type  = models.CharField(max_length=20, choices=DEVICE_TYPE)
    serial_number = models.CharField(max_length=100, unique=True)
    location     = models.CharField(max_length=200, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    api_token    = models.CharField(max_length=64, unique=True)
    status       = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    registered_at = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    last_ping    = models.DateTimeField(null=True, blank=True)
    total_pushes = models.BigIntegerField(default=0)
    firmware_version = models.CharField(max_length=50, blank=True)
    geo_lat      = models.FloatField(null=True, blank=True)
    geo_lon      = models.FloatField(null=True, blank=True)
    metadata     = models.JSONField(default=dict)

    class Meta:
        db_table = 'tap_iot_devices'
        ordering = ['-registered_at']

    def __str__(self): return f"{self.name} [{self.device_type}]"

    @staticmethod
    def generate_token(): return secrets.token_urlsafe(48)

    @property
    def status_color(self):
        return {'ACTIVE':'#10b981','INACTIVE':'#6b7280','ALERT':'#ef4444','MAINTENANCE':'#f59e0b'}.get(self.status,'#6b7280')


class IoTDataPush(models.Model):
    """Each data payload pushed by an IoT device."""
    VERDICT_CHOICES = [('CLEAN','Clean'),('SUSPICIOUS','Suspicious'),('ANOMALOUS','Anomalous'),('PENDING','Pending')]

    device       = models.ForeignKey(IoTDevice, on_delete=models.CASCADE, related_name='data_pushes')
    received_at  = models.DateTimeField(auto_now_add=True)
    payload_hash = models.CharField(max_length=64)
    payload_size = models.IntegerField(default=0)
    payload_type = models.CharField(max_length=50, default='json')
    verdict      = models.CharField(max_length=15, choices=VERDICT_CHOICES, default='PENDING')
    ai_score     = models.FloatField(default=0.0)
    evidence     = models.ForeignKey('tap_evidence.Evidence', null=True, blank=True, on_delete=models.SET_NULL)
    raw_preview  = models.TextField(blank=True)
    metadata     = models.JSONField(default=dict)

    class Meta:
        db_table = 'tap_iot_pushes'
        ordering = ['-received_at']

    def __str__(self): return f"{self.device.name} push @ {self.received_at:%Y-%m-%d %H:%M}"

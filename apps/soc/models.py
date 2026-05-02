"""TAP-DEV Phase 4 — Security Operations Center Models"""
from django.db import models
from django.contrib.auth.models import User


class SOCAlert(models.Model):
    SEVERITY = [('CRITICAL','Critical'),('HIGH','High'),('MEDIUM','Medium'),('LOW','Low'),('INFO','Info')]
    ALERT_TYPE = [
        ('AI_ANOMALY','AI Anomaly Detected'),('REPLAY_ATTACK','Replay Attack'),
        ('TIMESTAMP_TAMPER','Timestamp Tampering'),('CHAIN_BREAK','Chain Integrity Break'),
        ('IOT_INTRUSION','IoT Intrusion'),('MASS_UPLOAD','Mass Upload Spike'),
        ('INSIDER_THREAT','Insider Threat Signal'),('ZKP_FAIL','ZKP Verification Failed'),
        ('BLOCKCHAIN_FAIL','Blockchain Anchor Failed'),('GEO_ANOMALY','Geolocation Anomaly'),
    ]
    STATUS = [('OPEN','Open'),('INVESTIGATING','Investigating'),('RESOLVED','Resolved'),('FALSE_POSITIVE','False Positive')]

    organization  = models.ForeignKey('tap_org.Organization', null=True, blank=True, on_delete=models.SET_NULL, related_name='soc_alerts')
    alert_type    = models.CharField(max_length=30, choices=ALERT_TYPE)
    severity      = models.CharField(max_length=10, choices=SEVERITY, default='MEDIUM')
    status        = models.CharField(max_length=20, choices=STATUS, default='OPEN')
    title         = models.CharField(max_length=200)
    description   = models.TextField()
    evidence      = models.ForeignKey('tap_evidence.Evidence', null=True, blank=True, on_delete=models.SET_NULL)
    triggered_by_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    detected_at   = models.DateTimeField(auto_now_add=True)
    resolved_at   = models.DateTimeField(null=True, blank=True)
    resolved_by   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='resolved_alerts')
    source_ip     = models.GenericIPAddressField(null=True, blank=True)
    geo_country   = models.CharField(max_length=80, blank=True)
    geo_city      = models.CharField(max_length=80, blank=True)
    geo_lat       = models.FloatField(null=True, blank=True)
    geo_lon       = models.FloatField(null=True, blank=True)
    metadata      = models.JSONField(default=dict)
    ai_confidence = models.FloatField(default=0.0)

    class Meta:
        db_table = 'tap_soc_alerts'
        ordering = ['-detected_at']

    def __str__(self): return f"[{self.severity}] {self.title}"

    @property
    def severity_color(self):
        return {'CRITICAL':'#dc2626','HIGH':'#ef4444','MEDIUM':'#f59e0b','LOW':'#84cc16','INFO':'#00d4ff'}.get(self.severity,'#6b7280')

    @property
    def severity_icon(self):
        return {'CRITICAL':'🔴','HIGH':'🟠','MEDIUM':'🟡','LOW':'🟢','INFO':'🔵'}.get(self.severity,'⚪')


class LiveFeed(models.Model):
    """Real-time activity feed entries for the SOC dashboard."""
    FEED_TYPE = [('UPLOAD','Evidence Upload'),('AI_SCAN','AI Scan'),('BLOCKCHAIN','Blockchain TX'),
                 ('ALERT','Alert Triggered'),('LOGIN','User Login'),('IOT_PUSH','IoT Data Push')]
    feed_type   = models.CharField(max_length=20, choices=FEED_TYPE)
    organization = models.ForeignKey('tap_org.Organization', null=True, blank=True, on_delete=models.SET_NULL)
    user        = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    message     = models.CharField(max_length=300)
    icon        = models.CharField(max_length=10, default='●')
    color       = models.CharField(max_length=20, default='#00d4ff')
    timestamp   = models.DateTimeField(auto_now_add=True)
    metadata    = models.JSONField(default=dict)

    class Meta:
        db_table = 'tap_live_feed'
        ordering = ['-timestamp']

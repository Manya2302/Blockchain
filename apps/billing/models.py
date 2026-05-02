"""TAP-DEV Phase 4 — Billing & Subscription Models"""
import uuid
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [('FREE','Free'),('STARTER','Starter'),('PROFESSIONAL','Professional'),('ENTERPRISE','Enterprise'),('GOVERNMENT','Government')]
    name         = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    price_month  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_year   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users    = models.IntegerField(default=5)
    max_evidence_gb = models.FloatField(default=1.0)
    api_calls_day = models.IntegerField(default=100)
    ai_scans_month = models.IntegerField(default=50)
    blockchain_anchors = models.IntegerField(default=10)
    features     = models.JSONField(default=list)
    is_active    = models.BooleanField(default=True)
    class Meta:
        db_table = 'tap_subscription_plans'
    def __str__(self): return f"{self.name} (${self.price_month}/mo)"


class OrganizationSubscription(models.Model):
    STATUS_CHOICES = [('ACTIVE','Active'),('TRIALING','Trialing'),('PAST_DUE','Past Due'),('CANCELLED','Cancelled')]
    organization = models.OneToOneField('tap_org.Organization', on_delete=models.CASCADE, related_name='subscription')
    plan         = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status       = models.CharField(max_length=15, choices=STATUS_CHOICES, default='TRIALING')
    started_at   = models.DateTimeField(auto_now_add=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end    = models.DateTimeField(null=True, blank=True)
    stripe_sub_id = models.CharField(max_length=100, blank=True)
    api_calls_used = models.IntegerField(default=0)
    evidence_gb_used = models.FloatField(default=0.0)
    ai_scans_used = models.IntegerField(default=0)
    class Meta:
        db_table = 'tap_org_subscriptions'
    def __str__(self): return f"{self.organization.name} — {self.plan.name}"
    @property
    def is_active(self): return self.status in ('ACTIVE','TRIALING')
    @property
    def days_remaining(self):
        if self.current_period_end:
            d = (self.current_period_end - timezone.now()).days
            return max(d, 0)
        return 0


class UsageEvent(models.Model):
    EVENT_TYPE = [('API_CALL','API Call'),('EVIDENCE_UPLOAD','Upload'),('AI_SCAN','AI Scan'),('BLOCKCHAIN_TX','Blockchain TX'),('REPORT_GEN','Report')]
    organization = models.ForeignKey('tap_org.Organization', on_delete=models.CASCADE, related_name='usage_events')
    event_type   = models.CharField(max_length=20, choices=EVENT_TYPE)
    quantity     = models.FloatField(default=1.0)
    cost_units   = models.FloatField(default=0.0)
    timestamp    = models.DateTimeField(auto_now_add=True)
    metadata     = models.JSONField(default=dict)
    class Meta:
        db_table = 'tap_usage_events'
        ordering = ['-timestamp']

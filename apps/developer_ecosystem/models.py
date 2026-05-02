"""TAP-DEV Phase 5 — Developer Ecosystem & Marketplace"""
import uuid, secrets
from django.db import models
from django.contrib.auth.models import User


class MarketplacePlugin(models.Model):
    PLUGIN_TYPE = [("CONNECTOR","Data Connector"),("ANALYZER","Analysis Plugin"),
                   ("REPORTER","Report Template"),("VISUALIZER","Visualization"),
                   ("INTEGRATION","3rd Party Integration"),("WORKFLOW","Workflow Automation")]
    STATUS = [("PENDING","Pending Review"),("APPROVED","Approved"),("REJECTED","Rejected"),("DEPRECATED","Deprecated")]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    plugin_type = models.CharField(max_length=15, choices=PLUGIN_TYPE)
    description = models.TextField()
    version     = models.CharField(max_length=20)
    author      = models.ForeignKey(User, on_delete=models.CASCADE)
    status      = models.CharField(max_length=15, choices=STATUS, default="PENDING")
    price       = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    installs    = models.IntegerField(default=0)
    rating      = models.FloatField(default=0.0)
    ratings_count = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    api_endpoint = models.URLField(blank=True)
    webhook_url  = models.URLField(blank=True)
    permissions_required = models.JSONField(default=list)
    compatible_phases    = models.JSONField(default=list)
    changelog   = models.TextField(blank=True)
    is_certified = models.BooleanField(default=False)

    class Meta:
        db_table = "tap_marketplace_plugins"
        ordering = ["-installs"]

    def __str__(self): return f"{self.name} v{self.version} [{self.plugin_type}]"


class DeveloperApp(models.Model):
    STATUS = [("ACTIVE","Active"),("SUSPENDED","Suspended"),("REVOKED","Revoked")]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=100)
    developer    = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey("tap_org.Organization", null=True, on_delete=models.SET_NULL)
    client_id    = models.CharField(max_length=32, unique=True)
    client_secret_hash = models.CharField(max_length=64)
    status       = models.CharField(max_length=15, choices=STATUS, default="ACTIVE")
    redirect_uris = models.JSONField(default=list)
    scopes       = models.JSONField(default=list)
    created_at   = models.DateTimeField(auto_now_add=True)
    api_calls_total = models.BigIntegerField(default=0)
    last_active  = models.DateTimeField(null=True, blank=True)
    description  = models.TextField(blank=True)
    webhook_url  = models.URLField(blank=True)
    is_verified  = models.BooleanField(default=False)

    class Meta:
        db_table = "tap_developer_apps"
        ordering = ["-created_at"]

    def __str__(self): return f"{self.name} by {self.developer.username}"

    @staticmethod
    def generate_credentials():
        client_id = secrets.token_hex(16)
        secret = secrets.token_urlsafe(40)
        import hashlib
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        return client_id, secret, secret_hash

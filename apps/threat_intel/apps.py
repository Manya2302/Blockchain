from django.apps import AppConfig
class ThreatIntelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.threat_intel'
    label = 'tap_threat'
    verbose_name = 'Predictive Threat Intelligence'

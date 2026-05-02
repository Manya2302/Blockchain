from django.apps import AppConfig

class EvolutionTrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.evolution_tracker'
    label = 'tap_evolution'
    verbose_name = 'Document Evolution Tracker'

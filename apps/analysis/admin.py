from django.contrib import admin
from .models import Anomaly
@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display  = ['evidence','anomaly_type','severity','is_resolved','detected_at']
    list_filter   = ['severity','is_resolved','anomaly_type']
    readonly_fields = ['detected_at']

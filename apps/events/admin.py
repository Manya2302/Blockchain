from django.contrib import admin
from .models import Event
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id','evidence','event_type','actor','sequence_number','timestamp']
    list_filter  = ['event_type']
    readonly_fields = ['event_hash','timestamp']

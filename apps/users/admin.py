from django.contrib import admin
from .models import UserProfile, ActivityLog, OTPToken
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user','role','organization','department','created_at']
    list_filter  = ['role']
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user','action','category','ip_address','timestamp']
    list_filter  = ['category']
    readonly_fields = ['timestamp']
@admin.register(OTPToken)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['user','purpose','is_used','created_at','expires_at']

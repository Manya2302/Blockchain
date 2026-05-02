from django.contrib import admin
from .models import Evidence
@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ['id','title','uploader','status','trust_score','version','sha256_hash','created_at']
    list_filter  = ['status']
    search_fields= ['title','sha256_hash','case_id']
    readonly_fields = ['sha256_hash','created_at','updated_at']

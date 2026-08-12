from django.contrib import admin

from .models import DiagnosisBatch, DiagnosisItem, FarmerProfile, TreatmentGuide


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'village', 'district', 'state', 'preferred_language')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone', 'village')


class DiagnosisItemInline(admin.TabularInline):
    model = DiagnosisItem
    extra = 0
    fields = ('original_name', 'crop_name', 'disease_name', 'confidence', 'ai_status', 'review_status')
    readonly_fields = fields
    show_change_link = True


@admin.register(DiagnosisBatch)
class DiagnosisBatchAdmin(admin.ModelAdmin):
    list_display = ('title', 'farmer', 'status', 'original_file_count', 'image_count', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'farmer__username', 'farmer__first_name', 'farmer__last_name')
    inlines = [DiagnosisItemInline]


@admin.register(DiagnosisItem)
class DiagnosisItemAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'crop_name', 'disease_name', 'confidence', 'ai_status', 'review_status', 'created_at')
    list_filter = ('ai_status', 'review_status', 'crop_name', 'created_at')
    search_fields = ('original_name', 'predicted_class', 'crop_name', 'disease_name', 'batch__farmer__username')
    readonly_fields = ('top_predictions', 'guidance_snapshot', 'created_at')


@admin.register(TreatmentGuide)
class TreatmentGuideAdmin(admin.ModelAdmin):
    list_display = ('crop_name', 'disease_name', 'active', 'updated_at')
    list_filter = ('active', 'crop_name')
    search_fields = ('class_name', 'crop_name', 'disease_name')

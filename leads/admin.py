from django.contrib import admin

from .models import Lead, LeadPhoto


class LeadPhotoInline(admin.TabularInline):
    model = LeadPhoto
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "source", "phone", "email", "zip_code", "created_at")
    list_filter = ("status", "source")
    search_fields = ("name", "email", "phone", "zip_code")
    inlines = [LeadPhotoInline]


@admin.register(LeadPhoto)
class LeadPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "lead", "uploaded_at")

from django.contrib import admin

from .models import Job, JobPhoto


class JobPhotoInline(admin.TabularInline):
    model = JobPhoto
    extra = 0


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "status",
        "scheduled_date",
        "time_window",
        "completed_at",
    )
    list_filter = ("status",)
    inlines = [JobPhotoInline]


@admin.register(JobPhoto)
class JobPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "use_in_gallery", "uploaded_at")

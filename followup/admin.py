from django.contrib import admin

from .models import RecurringPlan, ReviewRequest


@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "job", "recipient_email", "sent_at")
    search_fields = ("customer__name", "recipient_email", "google_review_url")


@admin.register(RecurringPlan)
class RecurringPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "frequency",
        "next_service_date",
        "discount_percent",
        "is_active",
    )
    list_filter = ("frequency", "is_active")

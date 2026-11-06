from django.contrib import admin

from .models import Quote, QuoteLine, RateCard, RateCardItem


class RateCardItemInline(admin.TabularInline):
    model = RateCardItem
    extra = 0


@admin.register(RateCard)
class RateCardAdmin(admin.ModelAdmin):
    list_display = ("name", "minimum_charge", "updated_at")
    inlines = [RateCardItemInline]


@admin.register(RateCardItem)
class RateCardItemAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "unit", "unit_price", "is_addon", "is_active", "rate_card")
    list_filter = ("is_addon", "is_active", "unit")


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 0


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "status", "total", "created_at")
    list_filter = ("status",)
    inlines = [QuoteLineInline]

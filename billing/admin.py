from django.contrib import admin

from .models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total", "hosted_payment_url", "created_at")
    list_filter = ("status",)
    inlines = [InvoiceLineInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "amount", "method", "provider", "external_id", "recorded_at")
    list_filter = ("method",)

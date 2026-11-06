from django.contrib import admin

from .models import Customer, Property


class PropertyInline(admin.StackedInline):
    model = Property
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "customer_type", "created_at")
    search_fields = ("name", "phone", "email")
    inlines = [PropertyInline]


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("address_line1", "city", "zip_code", "customer")
    search_fields = ("address_line1", "city", "zip_code", "customer__name")

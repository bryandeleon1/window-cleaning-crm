"""URL configuration for the window-cleaning CRM."""

from django.contrib import admin
from django.urls import include, path

from leads import views as lead_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("owner/leads/", include("leads.urls")),
    path("owner/clients/", include("clients.urls")),
    path("owner/quotes/", include("quoting.urls")),
    path("owner/jobs/", include("jobs.urls")),
    path("owner/invoices/", include("billing.urls")),
    path("owner/followup/", include("followup.urls")),
    path("quote/", lead_views.public_quote, name="public_quote"),
    path("integrations/leads/", lead_views.inbound_webhook, name="leads_webhook"),
    path("", include("marketing.urls")),
]
# Lead/job photos are login-required — never public /media/.
# /admin/ stays enabled as Django's built-in tool; the product UI is login-only /owner/.
# Single-tenant: any logged-in owner can see all records (no per-object ACLs).

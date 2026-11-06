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
    path("quote/", lead_views.public_quote, name="public_quote"),
    path("integrations/leads/", lead_views.inbound_webhook, name="leads_webhook"),
    path("", include("marketing.urls")),
]
# Lead photos are served only via login-required leads:photo — never public /media/.

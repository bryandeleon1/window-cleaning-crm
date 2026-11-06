from django.urls import path

from . import views

app_name = "leads"

# Owner CRM lead routes (mounted at /owner/leads/)
urlpatterns = [
    path("", views.lead_list, name="list"),
    path("new/", views.phone_lead_create, name="phone_create"),
    path("<int:pk>/", views.lead_detail, name="detail"),
    path("<int:pk>/photos/<int:photo_id>/", views.lead_photo, name="photo"),
]

from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("", views.customer_list, name="list"),
    path("<int:pk>/", views.customer_detail, name="detail"),
    path("<int:pk>/edit/", views.customer_edit, name="edit"),
    path(
        "<int:pk>/properties/<int:property_pk>/edit/",
        views.property_edit,
        name="property_edit",
    ),
]

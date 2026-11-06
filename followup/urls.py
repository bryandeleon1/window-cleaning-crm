from django.urls import path

from . import views

app_name = "followup"

urlpatterns = [
    path("", views.followup_home, name="home"),
    path("jobs/<int:job_id>/review-ask/", views.send_review_ask, name="send_review_ask"),
    path(
        "customers/<int:customer_id>/properties/<int:property_id>/recurring/",
        views.recurring_plan_create,
        name="plan_create",
    ),
    path("plans/<int:pk>/", views.recurring_plan_detail, name="plan_detail"),
    path("plans/<int:pk>/edit/", views.recurring_plan_edit, name="plan_edit"),
]

from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.invoice_list, name="list"),
    path("<int:pk>/", views.invoice_detail, name="detail"),
    path("<int:pk>/payments/", views.payment_create, name="payment_create"),
    path("<int:pk>/hosted-url/", views.hosted_url_save, name="hosted_url_save"),
    path("from-job/<int:job_id>/", views.generate_from_job, name="generate_from_job"),
]

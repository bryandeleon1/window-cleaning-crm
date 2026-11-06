from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("services/", views.ServicesView.as_view(), name="services"),
    path("service-area/", views.ServiceAreaView.as_view(), name="service_area"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("gallery/", views.GalleryView.as_view(), name="gallery"),
    path("faq/", views.FAQView.as_view(), name="faq"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("quote/", views.ContactView.as_view(), name="quote"),
]

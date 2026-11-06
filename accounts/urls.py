from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.OwnerLoginView.as_view(), name="login"),
    path("logout/", views.OwnerLogoutView.as_view(), name="logout"),
    path("owner/", views.owner_home, name="home"),
]

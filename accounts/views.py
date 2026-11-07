"""Owner sign-in/out and the owner home screen. Every owner screen is login-only.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render


class OwnerLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class OwnerLogoutView(LogoutView):
    next_page = "accounts:login"


@login_required
def owner_home(request):
    """Phone-simple owner home stub (product UI, not Django admin)."""
    return render(request, "accounts/home.html")

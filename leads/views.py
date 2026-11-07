"""Lead screens and intake endpoints.

Views here only handle HTTP: forms, redirects, messages, status codes.
The rules for creating a lead live in leads/services.py.
"""

import hmac
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from marketing import demo as marketing_demo

from notifications.files import private_image_response

from .forms import LeadStatusForm, PhoneLeadForm, PublicQuoteForm
from .models import Lead, LeadPhoto
from .services import create_lead_from_webhook_payload, create_phone_lead, create_web_form_lead


def _marketing_context(**extra):
    ctx = {
        "brand_name": marketing_demo.BRAND_NAME,
        "owner_name": marketing_demo.OWNER_NAME,
        "phone_display": marketing_demo.PHONE_DISPLAY,
        "phone_tel": marketing_demo.PHONE_TEL,
        "time_zone_label": marketing_demo.TIME_ZONE_LABEL,
        "service_area_cities": marketing_demo.SERVICE_AREA_CITIES,
        "service_area_zips": marketing_demo.SERVICE_AREA_ZIPS,
        "core_services": marketing_demo.CORE_SERVICES,
        "addon_services": marketing_demo.ADDON_SERVICES,
        "not_offered": marketing_demo.NOT_OFFERED,
        "faq_items": marketing_demo.FAQ_ITEMS,
    }
    ctx.update(extra)
    return ctx


@require_http_methods(["GET", "POST"])
def public_quote(request):
    """Public quote/contact form — creates a lead and emails owner + customer."""
    if request.method == "POST":
        form = PublicQuoteForm(request.POST, request.FILES)
        if form.is_valid():
            create_web_form_lead(form.save(commit=False), form.cleaned_data.get("photos"))
            messages.success(
                request,
                "Thanks — we got your request and will follow up soon.",
            )
            return redirect("marketing:contact")
    else:
        form = PublicQuoteForm()
    return render(request, "marketing/contact.html", _marketing_context(form=form))


@login_required
def lead_list(request):
    leads = Lead.objects.all()
    status = request.GET.get("status")
    if status:
        leads = leads.filter(status=status)
    return render(
        request,
        "leads/lead_list.html",
        {"leads": leads, "statuses": Lead.Status.choices, "current_status": status or ""},
    )


@login_required
def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == "POST":
        form = LeadStatusForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            messages.success(request, "Lead updated.")
            return redirect("leads:detail", pk=lead.pk)
    else:
        form = LeadStatusForm(instance=lead)
    return render(request, "leads/lead_detail.html", {"lead": lead, "form": form})


@login_required
@require_GET
def lead_photo(request, pk, photo_id):
    """Serve a lead photo only to the logged-in owner (never via public /media/)."""
    photo = get_object_or_404(LeadPhoto, pk=photo_id, lead_id=pk)
    return private_image_response(photo.image)


@login_required
@require_http_methods(["GET", "POST"])
def phone_lead_create(request):
    """Owner logs a lead taken over the phone."""
    if request.method == "POST":
        form = PhoneLeadForm(request.POST)
        if form.is_valid():
            lead = create_phone_lead(form.save(commit=False))
            messages.success(request, "Phone lead logged.")
            return redirect("leads:detail", pk=lead.pk)
    else:
        form = PhoneLeadForm()
    return render(request, "leads/phone_lead_form.html", {"form": form})


def _webhook_secret_ok(request) -> bool:
    expected = getattr(settings, "LEADS_WEBHOOK_SECRET", "") or ""
    if not expected:
        return False
    provided = request.headers.get("X-Leads-Webhook-Secret", "")
    if not isinstance(provided, str) or not provided:
        return False
    # Constant-time compare so the secret cannot be guessed from response timing.
    return hmac.compare_digest(provided.encode("utf-8"), str(expected).encode("utf-8"))


# csrf_exempt is intentional: this is a machine-to-machine POST with no browser
# cookie. The shared-secret header stands in for CSRF, and an empty secret fails
# closed so a missing env var never leaves the endpoint open. No extra rate limit
# here or on the public quote form (single-owner demo).
@csrf_exempt
@require_POST
def inbound_webhook(request):
    """POST /integrations/leads/ — shared-secret header for a future live site."""
    if not _webhook_secret_ok(request):
        return HttpResponseForbidden("Invalid or missing webhook secret.")

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    name = (payload.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "name is required"}, status=400)

    lead, in_area = create_lead_from_webhook_payload(payload)
    return JsonResponse(
        {
            "ok": True,
            "lead_id": lead.pk,
            "zip_in_service_area": in_area,
        },
        status=201,
    )

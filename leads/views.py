import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from marketing import demo as marketing_demo

from .emails import send_new_lead_emails
from .forms import LeadStatusForm, PhoneLeadForm, PublicQuoteForm
from .models import Lead, LeadPhoto
from .service_area import normalize_zip, zip_in_service_area


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


def _save_optional_photo(lead: Lead, uploaded) -> None:
    if not uploaded:
        return
    LeadPhoto.objects.create(lead=lead, image=uploaded)


@require_http_methods(["GET", "POST"])
def public_quote(request):
    """Public quote/contact form — creates a lead and emails owner + customer."""
    if request.method == "POST":
        form = PublicQuoteForm(request.POST, request.FILES)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.source = Lead.Source.WEB_FORM
            lead.status = Lead.Status.NEW
            lead.zip_code = normalize_zip(lead.zip_code)
            lead.save()
            _save_optional_photo(lead, form.cleaned_data.get("photos"))
            send_new_lead_emails(lead)
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
@require_http_methods(["GET", "POST"])
def phone_lead_create(request):
    if request.method == "POST":
        form = PhoneLeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.source = Lead.Source.PHONE
            lead.status = Lead.Status.NEW
            lead.zip_code = normalize_zip(lead.zip_code)
            lead.save()
            send_new_lead_emails(lead)
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
    return provided == expected


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

    interest = payload.get("service_interest") or Lead.ServiceInterest.UNSURE
    valid_interests = {c.value for c in Lead.ServiceInterest}
    if interest not in valid_interests:
        interest = Lead.ServiceInterest.UNSURE

    zip_code = normalize_zip(payload.get("zip_code") or payload.get("zip") or "")
    lead = Lead.objects.create(
        name=name,
        email=(payload.get("email") or "").strip(),
        phone=(payload.get("phone") or "").strip(),
        address_line1=(payload.get("address_line1") or payload.get("address") or "").strip(),
        city=(payload.get("city") or "").strip(),
        zip_code=zip_code,
        service_interest=interest,
        message=(payload.get("message") or "").strip(),
        source=Lead.Source.WEBHOOK,
        status=Lead.Status.NEW,
    )
    in_area = zip_in_service_area(zip_code) if zip_code else None
    send_new_lead_emails(lead)
    return JsonResponse(
        {
            "ok": True,
            "lead_id": lead.pk,
            "zip_in_service_area": in_area,
        },
        status=201,
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from leads.models import Lead

from .emails import send_quote_email
from .forms import BuildQuoteForm, QuoteLoseForm, RateCardItemForm, RateCardSettingsForm
from .models import Quote, RateCardItem
from .services import accept_quote, build_quote_from_lead, ensure_default_rate_card, lose_quote


@login_required
def quote_list(request):
    quotes = Quote.objects.select_related("lead", "customer").all()
    return render(request, "quoting/quote_list.html", {"quotes": quotes})


@login_required
def quote_detail(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related("lead", "customer", "property").prefetch_related("lines"),
        pk=pk,
    )
    lose_form = QuoteLoseForm()
    return render(
        request,
        "quoting/quote_detail.html",
        {"quote": quote, "lose_form": lose_form},
    )


@login_required
@require_http_methods(["GET", "POST"])
def build_from_lead(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    card = ensure_default_rate_card()
    items = list(card.items.filter(is_active=True))
    if request.method == "POST":
        form = BuildQuoteForm(request.POST, items=items)
        if form.is_valid():
            quote = build_quote_from_lead(lead, form.cleaned_line_specs())
            if form.cleaned_data.get("notes"):
                quote.notes = form.cleaned_data["notes"]
                quote.save(update_fields=["notes", "updated_at"])
            messages.success(request, f"Draft quote #{quote.pk} created.")
            return redirect("quoting:detail", pk=quote.pk)
    else:
        initial = {}
        # Prefill a sensible qty from the lead window/pane estimate for matching core service.
        estimate = lead.window_pane_estimate or 0
        interest = lead.service_interest
        code_map = {
            Lead.ServiceInterest.EXTERIOR: "exterior",
            Lead.ServiceInterest.INTERIOR: "interior",
            Lead.ServiceInterest.BOTH: "both",
        }
        pref_code = code_map.get(interest)
        if pref_code and estimate:
            for item in items:
                if item.code == pref_code:
                    initial[f"qty_{item.pk}"] = estimate
                    break
        form = BuildQuoteForm(items=items, initial=initial)
    return render(
        request,
        "quoting/build_quote.html",
        {"lead": lead, "form": form, "items": items, "card": card},
    )


@login_required
@require_POST
def send_quote(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    try:
        send_quote_email(quote)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("quoting:detail", pk=quote.pk)
    quote.status = Quote.Status.SENT
    quote.sent_at = timezone.now()
    quote.save(update_fields=["status", "sent_at", "updated_at"])
    messages.success(request, "Quote emailed to the customer.")
    return redirect("quoting:detail", pk=quote.pk)


@login_required
@require_POST
def accept(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if quote.status == Quote.Status.LOST:
        messages.error(request, "A lost quote cannot be accepted.")
        return redirect("quoting:detail", pk=quote.pk)
    accept_quote(quote)
    messages.success(
        request,
        "Quote accepted. Customer and property created. (Job scheduling is PR 4.)",
    )
    return redirect("quoting:detail", pk=quote.pk)


@login_required
@require_POST
def lose(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    form = QuoteLoseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "A lost reason is required.")
        return redirect("quoting:detail", pk=quote.pk)
    try:
        lose_quote(quote, form.cleaned_data["lost_reason"])
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("quoting:detail", pk=quote.pk)
    messages.success(request, "Quote marked lost.")
    return redirect("quoting:detail", pk=quote.pk)


@login_required
@require_http_methods(["GET", "POST"])
def rate_card_edit(request):
    card = ensure_default_rate_card()
    settings_form = RateCardSettingsForm(instance=card)
    if request.method == "POST" and request.POST.get("form") == "settings":
        settings_form = RateCardSettingsForm(request.POST, instance=card)
        if settings_form.is_valid():
            settings_form.save()
            messages.success(request, "Minimum charge updated.")
            return redirect("quoting:rate_card")
    items = card.items.all()
    return render(
        request,
        "quoting/rate_card.html",
        {"card": card, "settings_form": settings_form, "items": items},
    )


@login_required
@require_http_methods(["GET", "POST"])
def rate_card_item_edit(request, item_id):
    card = ensure_default_rate_card()
    item = get_object_or_404(RateCardItem, pk=item_id, rate_card=card)
    if request.method == "POST":
        form = RateCardItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Rate card item updated.")
            return redirect("quoting:rate_card")
    else:
        form = RateCardItemForm(instance=item)
    return render(
        request,
        "quoting/rate_card_item_edit.html",
        {"form": form, "item": item},
    )

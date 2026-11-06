from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from jobs.models import Job

from .forms import HostedPaymentUrlForm, RecordPaymentForm
from .models import Invoice
from .services import generate_invoice_for_job, record_payment, save_hosted_payment_url


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related("customer", "job", "property").all()
    status = request.GET.get("status")
    if status:
        invoices = invoices.filter(status=status)
    return render(
        request,
        "billing/invoice_list.html",
        {
            "invoices": invoices,
            "statuses": Invoice.Status.choices,
            "current_status": status or "",
        },
    )


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "job", "property").prefetch_related(
            "lines", "payments"
        ),
        pk=pk,
    )
    return render(
        request,
        "billing/invoice_detail.html",
        {
            "invoice": invoice,
            "payment_form": RecordPaymentForm(initial={"amount": invoice.balance_due}),
            "url_form": HostedPaymentUrlForm(instance=invoice),
        },
    )


@login_required
@require_POST
def generate_from_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    invoice = generate_invoice_for_job(job)
    messages.success(request, f"Invoice #{invoice.pk} ready.")
    return redirect("billing:detail", pk=invoice.pk)


@login_required
@require_POST
def payment_create(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    form = RecordPaymentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Check the payment amount and method.")
        return redirect("billing:detail", pk=invoice.pk)
    try:
        record_payment(
            invoice,
            amount=form.cleaned_data["amount"],
            method=form.cleaned_data["method"],
            note=form.cleaned_data.get("note") or "",
            provider=form.cleaned_data.get("provider") or "",
            external_id=form.cleaned_data.get("external_id") or "",
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("billing:detail", pk=invoice.pk)
    messages.success(request, "Payment recorded.")
    return redirect("billing:detail", pk=invoice.pk)


@login_required
@require_POST
def hosted_url_save(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    form = HostedPaymentUrlForm(request.POST, instance=invoice)
    if form.is_valid():
        save_hosted_payment_url(invoice, form.cleaned_data.get("hosted_payment_url") or "")
        messages.success(
            request,
            "Hosted payment URL saved (placeholder only — nothing was charged).",
        )
    else:
        messages.error(request, "That URL looks invalid.")
    return redirect("billing:detail", pk=invoice.pk)

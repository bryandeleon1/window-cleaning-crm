"""Customer screens. Each customer has one service property (no multi-property
workflow). The owner can update contact details and that property's address
and access notes; customer type, COI, and billing terms are read-only here.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CustomerContactForm, PropertyEditForm
from .models import Customer, Property


@login_required
def customer_list(request):
    customers = Customer.objects.prefetch_related("properties").all()
    return render(request, "clients/customer_list.html", {"customers": customers})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(
        Customer.objects.prefetch_related("properties"),
        pk=pk,
    )
    from followup.models import RecurringPlan

    recurring_plans = RecurringPlan.objects.filter(customer=customer, is_active=True)
    return render(
        request,
        "clients/customer_detail.html",
        {"customer": customer, "recurring_plans": recurring_plans},
    )


@login_required
@require_http_methods(["GET", "POST"])
def customer_edit(request, pk):
    """Owner updates the customer's contact details and notes."""
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerContactForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Customer updated.")
        return redirect("clients:detail", pk=customer.pk)
    return render(
        request,
        "clients/edit_form.html",
        {"customer": customer, "form": form, "heading": f"Edit {customer.name}"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def property_edit(request, pk, property_pk):
    """Owner updates the customer's single property: address and access notes."""
    customer = get_object_or_404(Customer, pk=pk)
    prop = get_object_or_404(Property, pk=property_pk, customer=customer)
    form = PropertyEditForm(request.POST or None, instance=prop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Property updated.")
        return redirect("clients:detail", pk=customer.pk)
    return render(
        request,
        "clients/edit_form.html",
        {"customer": customer, "form": form, "heading": "Edit property"},
    )

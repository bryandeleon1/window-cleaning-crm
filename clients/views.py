from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Customer


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

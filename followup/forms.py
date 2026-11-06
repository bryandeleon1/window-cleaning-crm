from django import forms

from .models import RecurringPlan


class RecurringPlanForm(forms.ModelForm):
    class Meta:
        model = RecurringPlan
        fields = ["frequency", "next_service_date", "discount_percent", "notes"]
        widgets = {
            "next_service_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "discount_percent": forms.NumberInput(attrs={"min": 0, "max": 100, "step": "0.01"}),
        }

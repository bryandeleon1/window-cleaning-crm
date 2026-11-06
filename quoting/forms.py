from decimal import Decimal, InvalidOperation

from django import forms

from .models import Quote, RateCard, RateCardItem
from .services import ensure_default_rate_card


class RateCardSettingsForm(forms.ModelForm):
    class Meta:
        model = RateCard
        fields = ["minimum_charge"]


class RateCardItemForm(forms.ModelForm):
    class Meta:
        model = RateCardItem
        fields = ["name", "unit", "unit_price", "is_addon", "is_active", "sort_order"]


class BuildQuoteForm(forms.Form):
    """Quantities keyed by rate-card item id are posted as qty_<id>."""

    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, items=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = list(items or [])
        for item in self.items:
            self.fields[f"qty_{item.pk}"] = forms.DecimalField(
                required=False,
                min_value=Decimal("0"),
                max_digits=10,
                decimal_places=2,
                initial=Decimal("0"),
                label=f"{item.name} ({item.get_unit_display()} · ${item.unit_price})",
                widget=forms.NumberInput(attrs={"step": "1", "min": "0"}),
            )

    def cleaned_line_specs(self) -> list[dict]:
        specs = []
        for item in self.items:
            raw = self.cleaned_data.get(f"qty_{item.pk}")
            if raw is None:
                continue
            qty = Decimal(raw)
            if qty > 0:
                specs.append({"item": item, "quantity": qty})
        return specs

    def clean(self):
        cleaned = super().clean()
        # Need at least one positive qty — validate after fields clean.
        specs = []
        for item in self.items:
            key = f"qty_{item.pk}"
            if key in self.errors:
                continue
            raw = cleaned.get(key)
            try:
                qty = Decimal(raw or 0)
            except (InvalidOperation, TypeError):
                qty = Decimal("0")
            if qty > 0:
                specs.append(qty)
        if not specs:
            raise forms.ValidationError("Add at least one line quantity from the rate card.")
        return cleaned


class QuoteLoseForm(forms.Form):
    lost_reason = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Why was this quote lost?"}),
    )

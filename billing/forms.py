from django import forms

from .models import Invoice, Payment


class RecordPaymentForm(forms.Form):
    amount = forms.DecimalField(min_value=0.01, max_digits=10, decimal_places=2)
    method = forms.ChoiceField(choices=Payment.Method.choices)
    note = forms.CharField(required=False, max_length=255)
    provider = forms.CharField(
        required=False,
        max_length=40,
        help_text="Optional stub (e.g. stripe). Not a live charge.",
    )
    external_id = forms.CharField(
        required=False,
        max_length=120,
        help_text="Optional external reference id stub.",
    )


class HostedPaymentUrlForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["hosted_payment_url"]
        labels = {
            "hosted_payment_url": "Stripe Payment Link / hosted invoice URL (placeholder)",
        }
        help_texts = {
            "hosted_payment_url": (
                "Paste a future Stripe Payment Link or hosted invoice URL. "
                "Saving this field does not charge a card or call Stripe."
            ),
        }

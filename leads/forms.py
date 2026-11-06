from django import forms

from .models import Lead


class PublicQuoteForm(forms.ModelForm):
    photos = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={"accept": "image/*"}),
        help_text="Optional photo of the house or windows (stored privately).",
    )

    class Meta:
        model = Lead
        fields = [
            "name",
            "email",
            "phone",
            "address_line1",
            "city",
            "zip_code",
            "service_interest",
            "stories",
            "window_pane_estimate",
            "how_heard",
            "message",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "address_line1": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2"}),
            "zip_code": forms.TextInput(attrs={"autocomplete": "postal-code"}),
            "stories": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "window_pane_estimate": forms.NumberInput(attrs={"min": 1}),
            "message": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["phone"].required = True
        self.fields["stories"].required = False
        self.fields["window_pane_estimate"].required = False
        self.fields["how_heard"].required = False


class PhoneLeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            "name",
            "phone",
            "email",
            "address_line1",
            "city",
            "zip_code",
            "service_interest",
            "stories",
            "window_pane_estimate",
            "how_heard",
            "message",
            "owner_notes",
        ]
        widgets = {
            "stories": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "window_pane_estimate": forms.NumberInput(attrs={"min": 1}),
            "message": forms.Textarea(attrs={"rows": 3}),
            "owner_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required = True
        # Keep the phone form small: extra estimate fields stay optional.
        for name in ("stories", "window_pane_estimate", "how_heard", "email"):
            self.fields[name].required = False


class LeadStatusForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["status", "lost_reason", "owner_notes"]
        widgets = {
            "owner_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        lost_reason = (cleaned.get("lost_reason") or "").strip()
        if status == Lead.Status.LOST and not lost_reason:
            self.add_error("lost_reason", "A reason is required when marking a lead lost.")
        if status != Lead.Status.LOST:
            cleaned["lost_reason"] = ""
        return cleaned

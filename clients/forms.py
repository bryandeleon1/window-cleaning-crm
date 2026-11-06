from django import forms

from .models import Customer, Property


class CustomerContactForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "email", "phone", "notes"]


class PropertyEditForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "label",
            "address_line1",
            "city",
            "state",
            "zip_code",
            "access_pets",
            "access_alarms",
            "access_parking",
            "access_notes",
        ]

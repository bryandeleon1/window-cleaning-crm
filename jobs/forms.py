from django import forms

from notifications.images import validate_safe_image

from .models import Job, JobPhoto


class ScheduleJobForm(forms.Form):
    scheduled_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    time_window = forms.ChoiceField(
        choices=[
            ("", "Not set"),
            (Job.TimeWindow.MORNING, "Morning"),
            (Job.TimeWindow.AFTERNOON, "Afternoon"),
        ],
        required=False,
    )
    note = forms.CharField(required=False, max_length=255)
    as_reschedule = forms.BooleanField(required=False, initial=False)


class WeatherHoldForm(forms.Form):
    note = forms.CharField(
        required=False,
        max_length=255,
        initial="Weather hold",
        widget=forms.TextInput(attrs={"placeholder": "Rain / wind / freeze"}),
    )


class JobPhotoUploadForm(forms.ModelForm):
    class Meta:
        model = JobPhoto
        fields = ["image", "caption", "use_in_gallery"]
        widgets = {
            "image": forms.FileInput(attrs={"accept": "image/*"}),
            "caption": forms.TextInput(),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        validate_safe_image(image)
        return image

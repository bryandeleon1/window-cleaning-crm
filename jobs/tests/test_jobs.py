import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from jobs.models import Job, JobPhoto
from jobs.services import complete_job, ensure_job_for_quote, schedule_job, set_weather_hold
from leads.models import Lead
from quoting.services import accept_quote, build_quote_from_lead, ensure_default_rate_card

User = get_user_model()


class JobLifecycleTests(TestCase):
    def setUp(self):
        self.card = ensure_default_rate_card()
        self.exterior = self.card.items.get(code="exterior")
        self.lead = Lead.objects.create(
            name="Job Customer",
            email="job@example.com",
            phone="555-010-6000",
            address_line1="55 Pane Rd",
            city="Cedar Falls",
            zip_code="50613",
        )
        self.quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal("12")}],
        )

    def test_accept_quote_creates_a_job(self):
        accept_quote(self.quote)
        self.quote.refresh_from_db()
        job = Job.objects.get(quote=self.quote)
        self.assertEqual(job.status, Job.Status.UNSCHEDULED)
        self.assertEqual(job.customer_id, self.quote.customer_id)
        self.assertEqual(job.property_id, self.quote.property_id)

    def test_ensure_job_for_already_accepted_quote_without_job(self):
        # Simulate a quote accepted before jobs existed: accepted + customer/property, no job.
        accept_quote(self.quote)
        Job.objects.filter(quote=self.quote).delete()
        self.assertFalse(Job.objects.filter(quote=self.quote).exists())
        job = ensure_job_for_quote(self.quote)
        self.assertIsNotNone(job)
        self.assertEqual(Job.objects.filter(quote=self.quote).count(), 1)

    def test_schedule_and_weather_hold_reschedule(self):
        accept_quote(self.quote)
        job = Job.objects.get(quote=self.quote)
        day = date.today() + timedelta(days=3)
        schedule_job(job, scheduled_date=day, time_window=Job.TimeWindow.MORNING)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.SCHEDULED)
        self.assertEqual(job.scheduled_date, day)
        self.assertEqual(job.time_window, Job.TimeWindow.MORNING)

        set_weather_hold(job, note="High wind")
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.WEATHER_HOLD)
        self.assertEqual(job.status_note, "High wind")

        new_day = day + timedelta(days=2)
        schedule_job(
            job,
            scheduled_date=new_day,
            time_window=Job.TimeWindow.AFTERNOON,
            as_reschedule=True,
            note="After weather clears",
        )
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.RESCHEDULED)
        self.assertEqual(job.scheduled_date, new_day)
        self.assertEqual(job.time_window, Job.TimeWindow.AFTERNOON)

    def test_complete_sets_a_timestamp(self):
        accept_quote(self.quote)
        job = Job.objects.get(quote=self.quote)
        self.assertIsNone(job.completed_at)
        complete_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.COMPLETED)
        self.assertIsNotNone(job.completed_at)


class JobPhotoPrivacyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jordan", password="test-pass-12345")
        self._tmpdir = tempfile.TemporaryDirectory(prefix="wccrm-job-media-")
        self.addCleanup(self._tmpdir.cleanup)
        override = override_settings(MEDIA_ROOT=self._tmpdir.name, DEBUG=True)
        override.enable()
        self.addCleanup(override.disable)

        card = ensure_default_rate_card()
        lead = Lead.objects.create(
            name="Photo Job",
            email="pj@example.com",
            phone="555-010-6001",
            address_line1="1 Glass St",
            city="Waterloo",
            zip_code="50701",
        )
        quote = build_quote_from_lead(
            lead,
            [{"item": card.items.get(code="exterior"), "quantity": Decimal("5")}],
        )
        accept_quote(quote)
        self.job = Job.objects.get(quote=quote)
        upload = SimpleUploadedFile(
            "after.png",
            b"\x89PNG\r\n\x1a\n" + b"fake-job-photo",
            content_type="image/png",
        )
        self.photo = JobPhoto.objects.create(
            job=self.job,
            image=upload,
            use_in_gallery=True,
        )

    def test_unauthenticated_cannot_fetch_job_photo(self):
        url = reverse("jobs:photo", kwargs={"pk": self.job.pk, "photo_id": self.photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_authenticated_owner_can_fetch_job_photo(self):
        self.client.login(username="jordan", password="test-pass-12345")
        url = reverse("jobs:photo", kwargs={"pk": self.job.pk, "photo_id": self.photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_public_media_url_does_not_serve_job_photo(self):
        response = self.client.get(f"/media/{self.photo.image.name}")
        self.assertEqual(response.status_code, 404)

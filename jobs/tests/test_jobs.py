import io
import struct
import tempfile
import zlib
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from jobs.models import Job, JobPhoto
from jobs.services import complete_job, ensure_job_for_quote, schedule_job, set_weather_hold
from leads.models import Lead
from quoting.services import accept_quote, build_quote_from_lead, ensure_default_rate_card


def tiny_png(name="photo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (30, 120, 200)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def large_dimension_png(name="big.png", width=10000, height=10000):
    """Small PNG whose header declares dimensions over the pixel budget."""
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"")) + chunk(b"IEND", b"")
    return SimpleUploadedFile(name, data, content_type="image/png")


SVG_BYTES = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'

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
        upload = tiny_png("after.png")
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
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_upload_rejects_non_image_and_svg(self):
        self.client.login(username="jordan", password="test-pass-12345")
        url = reverse("jobs:photo_upload", kwargs={"pk": self.job.pk})
        for upload in (
            SimpleUploadedFile("a.jpg", b"plain text", content_type="image/jpeg"),
            SimpleUploadedFile("b.png", SVG_BYTES, content_type="image/png"),
        ):
            self.client.post(url, {"image": upload, "caption": "bad"})
        self.assertFalse(JobPhoto.objects.filter(caption="bad").exists())

    def test_upload_rejects_oversized_declared_dimensions(self):
        self.client.login(username="jordan", password="test-pass-12345")
        url = reverse("jobs:photo_upload", kwargs={"pk": self.job.pk})
        self.client.post(url, {"image": large_dimension_png(), "caption": "big"})
        self.assertFalse(JobPhoto.objects.filter(caption="big").exists())

    def test_stored_oversized_photo_returns_404(self):
        stored = JobPhoto.objects.create(job=self.job, image=large_dimension_png())
        self.client.login(username="jordan", password="test-pass-12345")
        url = reverse("jobs:photo", kwargs={"pk": self.job.pk, "photo_id": stored.pk})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_upload_accepts_small_image(self):
        self.client.login(username="jordan", password="test-pass-12345")
        url = reverse("jobs:photo_upload", kwargs={"pk": self.job.pk})
        self.client.post(url, {"image": tiny_png(), "caption": "good"})
        photo = JobPhoto.objects.get(caption="good")
        get_url = reverse("jobs:photo", kwargs={"pk": self.job.pk, "photo_id": photo.pk})
        self.assertEqual(self.client.get(get_url)["Content-Type"], "image/png")
        self.client.logout()
        self.assertEqual(self.client.get(get_url).status_code, 302)

    def test_public_media_url_does_not_serve_job_photo(self):
        response = self.client.get(f"/media/{self.photo.image.name}")
        self.assertEqual(response.status_code, 404)


class CompletedJobGuardTests(TestCase):
    def setUp(self):
        card = ensure_default_rate_card()
        lead = Lead.objects.create(name="Done", phone="555-010-6002", address_line1="2 Glass St")
        quote = build_quote_from_lead(
            lead, [{"item": card.items.get(code="exterior"), "quantity": Decimal("5")}]
        )
        accept_quote(quote)
        self.job = Job.objects.get(quote=quote)
        complete_job(self.job)
        self.job.refresh_from_db()
        self.completed_at = self.job.completed_at

    def _assert_unchanged(self):
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.COMPLETED)
        self.assertEqual(self.job.completed_at, self.completed_at)

    def test_services_refuse_or_noop_on_completed_job(self):
        with self.assertRaises(ValueError):
            schedule_job(self.job, scheduled_date=date.today())
        with self.assertRaises(ValueError):
            set_weather_hold(self.job, note="wind")
        complete_job(self.job)
        self._assert_unchanged()

    def test_canceled_job_is_terminal(self):
        Job.objects.filter(pk=self.job.pk).update(status=Job.Status.CANCELED)
        self.job.refresh_from_db()
        for call in (
            lambda: schedule_job(self.job, scheduled_date=date.today()),
            lambda: set_weather_hold(self.job),
            lambda: complete_job(self.job),
        ):
            with self.assertRaises(ValueError):
                call()

    def test_view_posts_leave_completed_job_alone(self):
        User.objects.create_user(username="owner", password="test-pass-12345")
        self.client.login(username="owner", password="test-pass-12345")
        pk = self.job.pk
        self.client.post(
            reverse("jobs:schedule", kwargs={"pk": pk}),
            {"scheduled_date": date.today().isoformat(), "time_window": "morning"},
        )
        self.client.post(reverse("jobs:weather_hold", kwargs={"pk": pk}), {"note": "x"})
        self.client.post(reverse("jobs:complete", kwargs={"pk": pk}))
        self._assert_unchanged()

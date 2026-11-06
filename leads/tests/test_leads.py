import io
import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from leads.models import Lead, LeadPhoto


def tiny_png(name="photo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (30, 120, 200)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


SVG_BYTES = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'

User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    OWNER_NOTIFY_EMAIL="owner@lakesidepane.example",
    DEFAULT_FROM_EMAIL="Lakeside Pane Co. <noreply@lakesidepane.example>",
    LEADS_WEBHOOK_SECRET="test-webhook-secret",
)
class PublicQuoteFormTests(TestCase):
    def test_public_quote_creates_lead_and_sends_emails(self):
        response = self.client.post(
            reverse("public_quote"),
            {
                "name": "Alex Neighbor",
                "email": "alex@example.com",
                "phone": "555-010-9999",
                "address_line1": "100 Main St",
                "city": "Cedar Falls",
                "zip_code": "50613",
                "service_interest": Lead.ServiceInterest.BOTH,
                "stories": "2",
                "window_pane_estimate": "22",
                "how_heard": Lead.HeardAbout.GOOGLE,
                "message": "Two-story exterior please",
            },
        )
        self.assertRedirects(response, reverse("marketing:contact"))
        lead = Lead.objects.get()
        self.assertEqual(lead.name, "Alex Neighbor")
        self.assertEqual(lead.source, Lead.Source.WEB_FORM)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.zip_code, "50613")
        self.assertEqual(lead.stories, 2)
        self.assertEqual(lead.window_pane_estimate, 22)
        self.assertEqual(lead.how_heard, Lead.HeardAbout.GOOGLE)
        self.assertEqual(len(mail.outbox), 2)
        subjects = {m.subject for m in mail.outbox}
        self.assertIn("New lead: Alex Neighbor", subjects)
        self.assertTrue(any("We got your quote request" in m.subject for m in mail.outbox))
        recipients = {addr for m in mail.outbox for addr in m.to}
        self.assertIn("owner@lakesidepane.example", recipients)
        self.assertIn("alex@example.com", recipients)


@override_settings(LEADS_WEBHOOK_SECRET="test-webhook-secret")
class WebhookTests(TestCase):
    def test_webhook_rejects_missing_secret(self):
        response = self.client.post(
            reverse("leads_webhook"),
            data=json.dumps({"name": "No Secret"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Lead.objects.count(), 0)

    def test_webhook_rejects_bad_secret(self):
        response = self.client.post(
            reverse("leads_webhook"),
            data=json.dumps({"name": "Bad Secret"}),
            content_type="application/json",
            headers={"X-Leads-Webhook-Secret": "wrong"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Lead.objects.count(), 0)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        OWNER_NOTIFY_EMAIL="owner@lakesidepane.example",
    )
    def test_webhook_accepts_valid_secret(self):
        response = self.client.post(
            reverse("leads_webhook"),
            data=json.dumps(
                {
                    "name": "Webflow Lead",
                    "email": "wf@example.com",
                    "phone": "555-010-1111",
                    "zip_code": "50701",
                    "stories": 1,
                    "window_pane_estimate": 12,
                    "how_heard": "referral",
                    "message": "From future live site",
                }
            ),
            content_type="application/json",
            headers={"X-Leads-Webhook-Secret": "test-webhook-secret"},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        lead = Lead.objects.get()
        self.assertEqual(lead.name, "Webflow Lead")
        self.assertEqual(lead.source, Lead.Source.WEBHOOK)
        self.assertEqual(lead.stories, 1)
        self.assertEqual(lead.window_pane_estimate, 12)
        self.assertEqual(lead.how_heard, Lead.HeardAbout.REFERRAL)
        self.assertTrue(payload["zip_in_service_area"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    OWNER_NOTIFY_EMAIL="owner@lakesidepane.example",
)
class OwnerPhoneLeadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jordan", password="test-pass-12345")
        self.client.login(username="jordan", password="test-pass-12345")

    def test_owner_phone_lead_form_creates_lead(self):
        response = self.client.post(
            reverse("leads:phone_create"),
            {
                "name": "Call-in Customer",
                "phone": "555-010-2222",
                "email": "",
                "address_line1": "",
                "city": "Waterloo",
                "zip_code": "50703",
                "service_interest": Lead.ServiceInterest.EXTERIOR,
                "stories": "",
                "window_pane_estimate": "",
                "how_heard": "",
                "message": "Called about screens",
                "owner_notes": "Prefers mornings",
            },
        )
        lead = Lead.objects.get()
        self.assertRedirects(response, reverse("leads:detail", kwargs={"pk": lead.pk}))
        self.assertEqual(lead.source, Lead.Source.PHONE)
        self.assertEqual(lead.phone, "555-010-2222")
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertIsNone(lead.stories)
        self.assertEqual(lead.how_heard, "")

    def test_owner_can_change_status_including_lost_reason(self):
        lead = Lead.objects.create(
            name="Status Lead",
            phone="555-010-3333",
            source=Lead.Source.PHONE,
        )
        response = self.client.post(
            reverse("leads:detail", kwargs={"pk": lead.pk}),
            {"status": Lead.Status.LOST, "lost_reason": "Too far", "owner_notes": ""},
        )
        self.assertRedirects(response, reverse("leads:detail", kwargs={"pk": lead.pk}))
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.LOST)
        self.assertEqual(lead.lost_reason, "Too far")

    def test_owner_detail_shows_quote_estimate_fields(self):
        lead = Lead.objects.create(
            name="Estimate Lead",
            phone="555-010-4444",
            stories=2,
            window_pane_estimate=18,
            how_heard=Lead.HeardAbout.NEXTDOOR,
        )
        response = self.client.get(reverse("leads:detail", kwargs={"pk": lead.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stories")
        self.assertContains(response, "Window/pane estimate")
        self.assertContains(response, "18")
        self.assertContains(response, "Nextdoor")


class LeadPhotoPrivacyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jordan", password="test-pass-12345")
        self._tmpdir = tempfile.TemporaryDirectory(prefix="wccrm-media-")
        self.addCleanup(self._tmpdir.cleanup)
        self.settings_override = override_settings(
            MEDIA_ROOT=self._tmpdir.name,
            DEBUG=True,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.lead = Lead.objects.create(name="Photo Lead", phone="555-010-5555")
        self.photo = LeadPhoto.objects.create(lead=self.lead, image=tiny_png("house.png"))

    def test_unauthenticated_cannot_fetch_lead_photo(self):
        url = reverse("leads:photo", kwargs={"pk": self.lead.pk, "photo_id": self.photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_authenticated_owner_can_fetch_lead_photo(self):
        self.client.login(username="jordan", password="test-pass-12345")
        url = reverse("leads:photo", kwargs={"pk": self.lead.pk, "photo_id": self.photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_stored_non_image_returns_404(self):
        bad = LeadPhoto.objects.create(
            lead=self.lead,
            image=SimpleUploadedFile("x.png", b"<html>hi</html>", content_type="image/png"),
        )
        self.client.login(username="jordan", password="test-pass-12345")
        url = reverse("leads:photo", kwargs={"pk": self.lead.pk, "photo_id": bad.pk})
        self.assertEqual(self.client.get(url).status_code, 404)

    def _post_quote(self, upload):
        return self.client.post(
            reverse("public_quote"),
            {
                "name": "Upload Lead",
                "email": "upload@example.com",
                "phone": "555-010-4444",
                "address_line1": "9 Elm",
                "city": "Waterloo",
                "zip_code": "50701",
                "service_interest": Lead.ServiceInterest.EXTERIOR,
                "photos": upload,
            },
        )

    def test_public_form_rejects_non_image_and_svg(self):
        for upload in (
            SimpleUploadedFile("notes.jpg", b"just some text", content_type="image/jpeg"),
            SimpleUploadedFile("pic.png", SVG_BYTES, content_type="image/png"),
        ):
            response = self._post_quote(upload)
            self.assertEqual(response.status_code, 200)
        self.assertFalse(Lead.objects.filter(name="Upload Lead").exists())

    def test_public_form_accepts_small_image_owner_can_view(self):
        response = self._post_quote(tiny_png())
        self.assertEqual(response.status_code, 302)
        photo = LeadPhoto.objects.get(lead__name="Upload Lead")
        url = reverse("leads:photo", kwargs={"pk": photo.lead_id, "photo_id": photo.pk})
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.login(username="jordan", password="test-pass-12345")
        self.assertEqual(self.client.get(url)["Content-Type"], "image/png")

    def test_public_media_url_does_not_serve_lead_photo(self):
        media_url = f"/media/{self.photo.image.name}"
        response = self.client.get(media_url)
        self.assertEqual(response.status_code, 404)


class MarketingPagesTests(TestCase):
    def test_public_pages_render(self):
        for name in [
            "marketing:home",
            "marketing:services",
            "marketing:service_area",
            "marketing:about",
            "marketing:gallery",
            "marketing:faq",
            "marketing:contact",
        ]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Lakeside Pane Co.")
                self.assertContains(response, "(555) 010-2040")

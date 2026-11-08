"""Direct tests for the lead intake services (no HTTP views involved)."""

import io
import tempfile

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from leads.models import Lead, LeadPhoto
from leads.services import (
    _finish_new_lead,
    create_lead_from_webhook_payload,
    create_phone_lead,
    create_web_form_lead,
)


def _tiny_png():
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buf, format="PNG")
    return SimpleUploadedFile("house.png", buf.getvalue(), content_type="image/png")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    OWNER_NOTIFY_EMAIL="owner@lakesidepane.example",
)
class LeadServiceTests(TestCase):
    def test_finish_new_lead_sets_channel_status_and_zip(self):
        lead = Lead(name="Zip Test", zip_code="50613-1234", status=Lead.Status.LOST)
        _finish_new_lead(lead, Lead.Source.PHONE)
        lead.refresh_from_db()
        self.assertEqual(lead.source, Lead.Source.PHONE)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.zip_code, "50613")

    def test_create_web_form_lead_saves_photo_and_emails_both(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with self.settings(MEDIA_ROOT=tmp.name):
            lead = create_web_form_lead(
                Lead(name="Web", email="web@example.com", zip_code=" 50701 "),
                _tiny_png(),
            )
        self.assertEqual(lead.source, Lead.Source.WEB_FORM)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.zip_code, "50701")
        self.assertEqual(LeadPhoto.objects.filter(lead=lead).count(), 1)
        recipients = {addr for m in mail.outbox for addr in m.to}
        self.assertEqual(recipients, {"owner@lakesidepane.example", "web@example.com"})

    def test_create_web_form_lead_without_photo(self):
        lead = create_web_form_lead(Lead(name="No Photo", zip_code=""))
        self.assertFalse(LeadPhoto.objects.filter(lead=lead).exists())
        # No customer email: only the owner is notified.
        self.assertEqual([m.to for m in mail.outbox], [["owner@lakesidepane.example"]])

    def test_create_phone_lead(self):
        lead = create_phone_lead(Lead(name="Caller", phone="555-010-1111", zip_code="50613"))
        self.assertEqual(lead.source, Lead.Source.PHONE)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(len(mail.outbox), 1)

    def test_webhook_payload_aliases_and_in_area_flag(self):
        lead, in_area = create_lead_from_webhook_payload(
            {
                "name": "  Hook  ",
                "email": "hook@example.com",
                "zip": "50613",
                "address": "1 Alias St",
                "window_count": "14",
                "heard_about": Lead.HeardAbout.GOOGLE,
                "service_interest": Lead.ServiceInterest.BOTH,
                "stories": "2",
            }
        )
        self.assertEqual(lead.name, "Hook")
        self.assertEqual(lead.zip_code, "50613")
        self.assertEqual(lead.address_line1, "1 Alias St")
        self.assertEqual(lead.window_pane_estimate, 14)
        self.assertEqual(lead.stories, 2)
        self.assertEqual(lead.how_heard, Lead.HeardAbout.GOOGLE)
        self.assertEqual(lead.source, Lead.Source.WEBHOOK)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertIs(in_area, True)
        self.assertEqual(len(mail.outbox), 2)

    def test_webhook_payload_fallbacks(self):
        lead, in_area = create_lead_from_webhook_payload(
            {
                "name": "Out",
                "zip_code": "90210",
                "pane_estimate": "lots",
                "how_heard": "billboard",
                "service_interest": "roof",
            }
        )
        self.assertEqual(lead.service_interest, Lead.ServiceInterest.UNSURE)
        self.assertIsNone(lead.window_pane_estimate)
        self.assertEqual(lead.how_heard, "")
        self.assertIs(in_area, False)

    def test_webhook_payload_without_zip_has_unknown_area(self):
        _lead, in_area = create_lead_from_webhook_payload({"name": "No Zip"})
        self.assertIsNone(in_area)

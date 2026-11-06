from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from notifications.sms import send


class ProjectChecksTests(SimpleTestCase):
    def test_django_checks_pass(self):
        # Raises SystemCheckError on failure.
        call_command("check")


class SmsStubTests(TestCase):
    def test_sms_send_is_noop(self):
        # Must not raise; stub logs/no-ops.
        send(to="+15550102040", body="Stub message")

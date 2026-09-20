import unittest

from app.email import EmailMessage
from app.parsers.detector import detect_vendor
from app.vendors import is_workday_sender


def message(sender: str) -> EmailMessage:
    return {
        "provider_id": "gmail-1",
        "sender": sender,
        "subject": "Application update",
        "raw_email": "",
        "received_at": None,
    }


class VendorDetectionTests(unittest.TestCase):
    def test_accepts_workday_notification_domains(self) -> None:
        self.assertTrue(is_workday_sender("notifications@myworkday.com"))
        self.assertTrue(is_workday_sender("no-reply@jobs.company.myworkday.com"))

    def test_rejects_other_or_malformed_senders(self) -> None:
        self.assertFalse(is_workday_sender("hiring@greenhouse.io"))
        self.assertFalse(is_workday_sender("myworkday.com"))
        self.assertFalse(is_workday_sender(""))

    def test_detects_workday_vendor(self) -> None:
        self.assertEqual(detect_vendor(message("alerts@myworkday.com")), "workday")
        self.assertIsNone(detect_vendor(message("hiring@greenhouse.io")))

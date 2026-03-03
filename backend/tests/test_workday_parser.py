import unittest

from app.parsers.workday import parse_workday_email


class WorkdayParserTests(unittest.TestCase):
    def test_parses_structured_plain_text_email(self) -> None:
        raw_email = """
        Thank you for applying to Acme Corp.
        Job Title: Senior Software Engineer
        Company: Acme Corp
        Location: Remote, US
        Requisition ID: R-12345
        Status: Application Received
        Applied on: February 19, 2026
        """
        parsed = parse_workday_email(raw_email, sender_email="notifications@myworkday.com")

        self.assertEqual(parsed.vendor, "workday")
        self.assertEqual(parsed.job_title, "Senior Software Engineer")
        self.assertEqual(parsed.company, "Acme Corp")
        self.assertEqual(parsed.location, "Remote, US")
        self.assertEqual(parsed.requisition_id, "R-12345")
        self.assertEqual(parsed.status, "applied")
        self.assertIsNotNone(parsed.applied_at)

    def test_parses_html_email(self) -> None:
        raw_email = """
        <html>
          <body>
            <p>Thank you for applying to Globex Inc via Workday.</p>
            <div>Position: Data Analyst</div>
            <div>Work Location: Austin, TX</div>
            <div>Req ID: GLOB-991</div>
            <div>Current Status: Under Review</div>
            <div>Application Date: 2026-02-18</div>
          </body>
        </html>
        """
        parsed = parse_workday_email(raw_email, sender_email="no-reply@myworkday.com")

        self.assertEqual(parsed.company, "Globex Inc")
        self.assertEqual(parsed.job_title, "Data Analyst")
        self.assertEqual(parsed.location, "Austin, TX")
        self.assertEqual(parsed.requisition_id, "GLOB-991")
        self.assertEqual(parsed.status, "under_review")
        self.assertIsNotNone(parsed.applied_at)

    def test_rejection_status_detected_from_body_text(self) -> None:
        raw_email = """
        Update regarding your application
        Company: Initech
        Position Applied For: Backend Engineer
        Thank you for your interest.
        You are no longer under consideration for this role.
        """
        parsed = parse_workday_email(raw_email, sender_email="careers@myworkday.com")
        self.assertEqual(parsed.status, "rejected")
        self.assertEqual(parsed.company, "Initech")
        self.assertEqual(parsed.job_title, "Backend Engineer")

    def test_handles_missing_fields(self) -> None:
        raw_email = "Thanks for your application."
        parsed = parse_workday_email(raw_email, sender_email="alerts@myworkday.com")
        self.assertEqual(parsed.vendor, "workday")
        self.assertIsNone(parsed.job_title)
        self.assertIsNone(parsed.company)
        self.assertIsNone(parsed.status)

    def test_rejects_non_myworkday_sender(self) -> None:
        raw_email = "Thank you for applying to Acme Corp."
        with self.assertRaises(ValueError):
            parse_workday_email(raw_email, sender_email="hiring@greenhouse.io")


if __name__ == "__main__":
    unittest.main()

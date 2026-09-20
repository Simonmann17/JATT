import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.gmail_client import fetch_gmail_messages

class GmailClientTests(unittest.TestCase):
	@patch("app.gmail_client._build_service")
	def test_fetches_and_normalize_gmail_message(self, build_service: Mock) -> None:
		service = Mock()
		build_service.return_value = service

		users = service.users.return_value
		messages_api = users.messages.return_value

		list_request = messages_api.list.return_value
		list_request.execute.return_value = {
			"messages": [{"id": "gmail-123"}]
		}

		get_request = messages_api.get.return_value

		get_request.execute.return_value = {
			"id": "gmail-123",
			"internalDate": "1760000000000",
			"payload": {
				"headers": [
					{
						"name": "From",
						"value": "Notifications <alerts@myworkday.com>",
					},
					{
						"name": "Subject",
						"value": "Application received",
					},
				],
				"body": {},
				"parts": [
					{
						"mimeType": "text/plain",
						"body": {
							"data": "VGhhbmsgeW91IGZvciBhcHBseWluZy4="
						},
					}
				],
			},
		}

		messages = fetch_gmail_messages(limit=1, lookback_days=30)

		self.assertEqual(len(messages), 1) #tests that only one message is received and parsed
		self.assertEqual(messages[0]["provider_id"], "gmail-123")
		self.assertEqual(messages[0]["sender"], "alerts@myworkday.com")
		self.assertEqual(messages[0]["subject"], "Application received")
		self.assertEqual(messages[0]["raw_email"], "Thank you for applying.")
		self.assertEqual(
            messages[0]["received_at"],
            datetime.fromtimestamp(
                1760000000000 / 1000,
                tz=timezone.utc,
            ),
        )

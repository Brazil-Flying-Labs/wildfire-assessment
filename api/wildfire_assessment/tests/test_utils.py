import smtplib
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from wildfire_assessment.utils import send_gmail_email


class SendGmailEmailTests(SimpleTestCase):
    def setUp(self):
        self.username = "no-reply@example.com"
        self.password = "pass1234"
        self.to_address = "user@example.com"
        self.subject = "Subject"
        self.body = "Body"

    @patch("wildfire_assessment.utils.smtplib.SMTP_SSL")
    def test_send_gmail_email_success(self, mock_smtp_cls):
        smtp_instance = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = smtp_instance

        send_gmail_email(
            username=self.username,
            password=self.password,
            to_address=self.to_address,
            subject=self.subject,
            body=self.body,
        )

        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 465)
        smtp_instance.login.assert_called_once_with(self.username, self.password)
        smtp_instance.send_message.assert_called_once()
        message_sent = smtp_instance.send_message.call_args.args[0]
        self.assertEqual(message_sent["From"], self.username)
        self.assertEqual(message_sent["To"], self.to_address)
        self.assertEqual(message_sent["Subject"], self.subject)
        self.assertEqual(message_sent.get_content().strip(), self.body)

    @patch("wildfire_assessment.utils.smtplib.SMTP_SSL")
    def test_send_gmail_email_raises_runtime_error_on_auth_failure(
        self, mock_smtp_cls
    ):
        smtp_instance = MagicMock()
        smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"auth")
        mock_smtp_cls.return_value.__enter__.return_value = smtp_instance

        with self.assertRaises(RuntimeError):
            send_gmail_email(
                username=self.username,
                password=self.password,
                to_address=self.to_address,
                subject=self.subject,
                body=self.body,
            )

        smtp_instance.send_message.assert_not_called()

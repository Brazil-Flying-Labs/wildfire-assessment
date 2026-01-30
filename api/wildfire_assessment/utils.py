import smtplib
from email.message import EmailMessage


def send_gmail_email(
    username: str, password: str, to_address: str, subject: str, body: str
) -> None:
    """Send a simple plain-text email using Gmail's SMTP servers.

    Gmail requires either OAuth or an app password when 2FA is enabled. For local
    development use an app password. The function raises smtplib.SMTPException on
    failures so callers can handle retries/logging as needed.
    """

    message = EmailMessage()
    message["From"] = username
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:  # pragma: no cover - network call
        raise RuntimeError(
            "Gmail rejected the credentials. Generate a Mail app password after enabling 2-Step Verification "
            "and update the backend secrets (see README.md#gmail-smtp-setup)."
        ) from exc

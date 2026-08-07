"""Email delivery for account verification."""
import asyncio
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    pass


async def send_verification_email(recipient: str, verification_url: str) -> None:
    subject = "Verify your Saki Gateway account"
    text = (
        "Verify your Saki Gateway account by opening this link:\n\n"
        f"{verification_url}\n\n"
        f"This link expires in {settings.VERIFICATION_TOKEN_HOURS} hours."
    )
    html = (
        "<p>Verify your Saki Gateway account by clicking the button below.</p>"
        f'<p><a href="{verification_url}">Verify email address</a></p>'
        f"<p>This link expires in {settings.VERIFICATION_TOKEN_HOURS} hours.</p>"
    )
    if settings.CF_EMAIL_API_TOKEN:
        if not settings.EMAIL_FROM:
            raise EmailDeliveryError("EMAIL_FROM must be configured with Cloudflare Email Service")
        if not settings.CF_ACCOUNT_ID:
            raise EmailDeliveryError("CF_ACCOUNT_ID must be configured with Cloudflare Email Service")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{settings.CF_ACCOUNT_ID}/email/sending/send",
                    headers={"Authorization": f"Bearer {settings.CF_EMAIL_API_TOKEN}", "Content-Type": "application/json"},
                    json={"from": settings.EMAIL_FROM, "to": recipient, "subject": subject, "text": text, "html": html},
                )
            payload = response.json()
            if response.status_code >= 400 or not payload.get("success"):
                raise EmailDeliveryError(f"Cloudflare Email Service rejected message: {response.status_code}")
            return
        except (httpx.HTTPError, EmailDeliveryError) as exc:
            raise EmailDeliveryError(str(exc)) from exc
    if settings.RESEND_API_KEY:
        if not settings.EMAIL_FROM:
            raise EmailDeliveryError("EMAIL_FROM must be configured with RESEND_API_KEY")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"from": settings.EMAIL_FROM, "to": [recipient], "subject": subject, "text": text, "html": html},
                )
            if response.status_code >= 400:
                raise EmailDeliveryError(f"Email provider rejected message: {response.status_code}")
            return
        except (httpx.HTTPError, EmailDeliveryError) as exc:
            raise EmailDeliveryError(str(exc)) from exc
    if settings.SMTP_HOST:
        if not settings.EMAIL_FROM:
            raise EmailDeliveryError("EMAIL_FROM must be configured with SMTP")
        try:
            await asyncio.wait_for(asyncio.to_thread(_send_smtp, recipient, subject, text, html), timeout=settings.SMTP_TIMEOUT_SECONDS + 2)
        except (TimeoutError, OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("SMTP delivery failed or timed out") from exc
        return
    raise EmailDeliveryError("No email provider configured")


def _send_smtp(recipient: str, subject: str, text: str, html: str) -> None:
    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as server:
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)

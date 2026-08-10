"""Brevo REST API delivery for account verification."""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        detail = payload.get("message") or payload.get("code") or payload
    except ValueError:
        detail = response.text
    return str(detail)[:500]


async def send_verification_email(recipient: str, verification_code: str) -> None:
    if not settings.BREVO_API_KEY:
        raise EmailDeliveryError("BREVO_API_KEY is not configured")
    if not settings.EMAIL_FROM:
        raise EmailDeliveryError("EMAIL_FROM is not configured")

    subject = "Your Saki Gateway verification code"
    text = (
        "Your Saki Gateway verification code is:\n\n"
        f"{verification_code}\n\n"
        "Enter this code on the Saki Gateway verification page. "
        f"It expires in {settings.VERIFICATION_CODE_MINUTES} minutes."
    )
    html = (
        "<p>Your Saki Gateway verification code is:</p>"
        f'<p style="font-size:28px;font-weight:700;letter-spacing:0.35em">{verification_code}</p>'
        "<p>Enter this code on the Saki Gateway verification page.</p>"
        f"<p>This code expires in {settings.VERIFICATION_CODE_MINUTES} minutes.</p>"
    )
    payload = {
        "sender": {"email": settings.EMAIL_FROM, "name": settings.EMAIL_FROM_NAME},
        "to": [{"email": recipient}],
        "subject": subject,
        "textContent": text,
        "htmlContent": html,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.EMAIL_API_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        logger.exception("Brevo REST request failed: %s", exc)
        raise EmailDeliveryError("Brevo email service is unreachable") from exc

    if response.status_code < 200 or response.status_code >= 300:
        detail = _response_detail(response)
        logger.error(
            "Brevo REST rejected verification code email: status=%s body=%s",
            response.status_code,
            detail,
        )
        raise EmailDeliveryError(
            f"Brevo rejected the verification email ({response.status_code}): {detail}"
        ) from None

    try:
        result = response.json()
    except ValueError as exc:
        logger.error(
            "Brevo REST returned non-JSON success response: status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
        raise EmailDeliveryError("Brevo returned an invalid success response") from exc

    logger.info("Brevo REST verification code response: %s", result)
    if not result.get("messageId"):
        logger.error("Brevo REST success response did not contain messageId: %s", str(result)[:500])
        raise EmailDeliveryError("Brevo did not confirm the verification email")

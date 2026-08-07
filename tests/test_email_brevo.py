import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
os.environ["BREVO_API_KEY"] = "test-key"
os.environ["EMAIL_FROM"] = "noreply@example.com"
os.environ["EMAIL_FROM_NAME"] = "Saki Gateway"

from app.services import email

class FakeResponse:
    def __init__(self, status_code=201, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

class FakeClient:
    def __init__(self, response):
        self.response = response
        self.payload = None
        self.headers = None
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def post(self, url, headers, json):
        assert url == "https://api.brevo.com/v3/smtp/email"
        assert headers["api-key"] == "test-key"
        assert "sender" in json and "to" in json and "htmlContent" in json
        self.payload = json
        return self.response

async def main():
    old = email.httpx.AsyncClient
    email.httpx.AsyncClient = lambda **kwargs: FakeClient(FakeResponse(payload={"messageId": "<test>"}))
    await email.send_verification_email("user@example.com", "https://example.com/verify?token=x")
    email.httpx.AsyncClient = lambda **kwargs: FakeClient(FakeResponse(status_code=401, payload={"message": "Key not found"}))
    try:
        await email.send_verification_email("user@example.com", "https://example.com/verify?token=x")
    except email.EmailDeliveryError as exc:
        assert "Key not found" in str(exc)
    else:
        raise AssertionError("Brevo rejection must fail")
    email.httpx.AsyncClient = old
    print("Brevo REST email checks: PASS")

asyncio.run(main())

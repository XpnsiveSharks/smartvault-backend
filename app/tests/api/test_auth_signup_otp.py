from __future__ import annotations

from unittest.mock import AsyncMock
from app.api.deps.auth import get_rate_limiter
from app.infrastructure.security.rate_limiter import RateLimitExceeded


def test_signup_happy_path(client, capture_email_service):
    email = "a@example.com"
    password = "verylongpassword!"
    full_name = "Alice Wonderland"

    # 1) Request OTP (sends email)
    r1 = client.post("/api/v1/auth/request-otp", json={"email": email})
    assert r1.status_code == 204, r1.text

    otp = capture_email_service.latest_otp_for(email)
    assert otp is not None
    assert len(otp) == 6

    # 2) Verify OTP -> returns signup ticket
    r2 = client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp})
    assert r2.status_code == 200, r2.text
    ticket = r2.json()["signup_ticket"]
    assert isinstance(ticket, str) and len(ticket) >= 20

    # 3) Signup using ticket -> creates user
    r3 = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "signup_ticket": ticket,
        },
    )
    assert r3.status_code == 201, r3.text
    body = r3.json()
    assert body["email"] == email
    assert body["full_name"] == full_name
    assert "id" in body
    assert "created_at" in body


def test_signup_rejects_reused_ticket(client, capture_email_service):
    email = "b@example.com"
    password = "verylongpassword!"

    # request otp
    r1 = client.post("/api/v1/auth/request-otp", json={"email": email})
    assert r1.status_code == 204, r1.text
    otp = capture_email_service.latest_otp_for(email)
    assert otp is not None

    # verify otp -> ticket
    r2 = client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp})
    assert r2.status_code == 200, r2.text
    ticket = r2.json()["signup_ticket"]

    # first signup ok
    r3 = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "signup_ticket": ticket},
    )
    assert r3.status_code == 201, r3.text

    # second signup with same ticket should fail (ticket is one-time)
    r4 = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "signup_ticket": ticket},
    )
    assert r4.status_code == 422, r4.text


def test_verify_otp_rejects_wrong_code(client):
    email = "c@example.com"

    # request otp
    r1 = client.post("/api/v1/auth/request-otp", json={"email": email})
    assert r1.status_code == 204, r1.text

    # wrong otp
    r2 = client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": "000000"})
    assert r2.status_code == 422, r2.text


def test_request_otp_email_rate_limit(monkeypatch, client):
    limiter = next(get_rate_limiter())
    call_counts = {"email": 0}

    async def fake_allow_request(*, key: str, limit: int, window_seconds: int):
        if key.startswith("otp_req:email:"):
            call_counts["email"] += 1
            if call_counts["email"] > 3:
                raise RateLimitExceeded()
        # allow other keys

    monkeypatch.setattr(limiter, "allow_request", AsyncMock(side_effect=fake_allow_request))

    email = "victim@test.com"
    for _ in range(3):
        resp = client.post("/api/v1/auth/request-otp", json={"email": email})
        assert resp.status_code == 204, resp.text

    resp = client.post("/api/v1/auth/request-otp", json={"email": email})
    assert resp.status_code == 429, resp.text




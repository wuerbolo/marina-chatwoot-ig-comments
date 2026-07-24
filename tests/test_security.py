import hashlib
import hmac

from app.security import verify_chatwoot_signature, verify_meta_signature

SECRET = "test-secret"
BODY = b'{"hello": "world"}'


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_meta_signature_valid():
    header = f"sha256={_sign(BODY, SECRET)}"
    assert verify_meta_signature(BODY, header, SECRET) is True


def test_verify_meta_signature_invalid():
    header = "sha256=deadbeef"
    assert verify_meta_signature(BODY, header, SECRET) is False


def test_verify_meta_signature_missing_prefix():
    header = _sign(BODY, SECRET)
    assert verify_meta_signature(BODY, header, SECRET) is False


def test_verify_meta_signature_missing_header():
    assert verify_meta_signature(BODY, None, SECRET) is False


def _sign_chatwoot(body: bytes, timestamp: str, secret: str) -> str:
    message = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def test_verify_chatwoot_signature_valid():
    timestamp = "1700000000"
    header = f"sha256={_sign_chatwoot(BODY, timestamp, SECRET)}"
    assert verify_chatwoot_signature(BODY, timestamp, header, SECRET) is True


def test_verify_chatwoot_signature_invalid():
    assert verify_chatwoot_signature(BODY, "1700000000", "sha256=deadbeef", SECRET) is False


def test_verify_chatwoot_signature_missing_prefix():
    timestamp = "1700000000"
    header = _sign_chatwoot(BODY, timestamp, SECRET)
    assert verify_chatwoot_signature(BODY, timestamp, header, SECRET) is False


def test_verify_chatwoot_signature_missing_timestamp():
    header = f"sha256={_sign_chatwoot(BODY, '1700000000', SECRET)}"
    assert verify_chatwoot_signature(BODY, None, header, SECRET) is False


def test_verify_chatwoot_signature_missing_header():
    assert verify_chatwoot_signature(BODY, "1700000000", None, SECRET) is False

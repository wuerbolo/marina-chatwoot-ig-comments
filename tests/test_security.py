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


def test_verify_chatwoot_signature_valid():
    header = _sign(BODY, SECRET)
    assert verify_chatwoot_signature(BODY, header, SECRET) is True


def test_verify_chatwoot_signature_invalid():
    assert verify_chatwoot_signature(BODY, "deadbeef", SECRET) is False


def test_verify_chatwoot_signature_missing_header():
    assert verify_chatwoot_signature(BODY, None, SECRET) is False

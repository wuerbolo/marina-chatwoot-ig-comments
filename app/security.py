import hashlib
import hmac


def verify_meta_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Valida X-Hub-Signature-256 (HMAC-SHA256 sobre el body crudo)."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


def verify_chatwoot_signature(body: bytes, signature_header: str | None, webhook_secret: str) -> bool:
    """Valida la firma HMAC-SHA256 del webhook saliente de Chatwoot."""
    if not signature_header:
        return False
    expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def relay_to_chatwoot(body: bytes, signature: str | None) -> None:
    """Reenvía el payload crudo de Meta a Chatwoot, tal cual, para no romper
    su canal de DM de Instagram (que dejó de ser el callback directo de Meta
    al pasar a serlo este servicio). Reenvía el body sin tocar y la misma
    firma X-Hub-Signature-256 que mandó Meta, para que la verificación de
    Chatwoot (mismo App Secret) siga siendo válida."""
    url = f"{settings.chatwoot_base_url}/webhooks/instagram"
    headers = {"Content-Type": "application/json"}
    if signature:
        headers["X-Hub-Signature-256"] = signature

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, content=body, headers=headers)
        if response.is_error:
            logger.warning(
                "Fallo al reenviar webhook de Instagram a Chatwoot: %s %s",
                response.status_code,
                response.text,
            )
    except httpx.HTTPError:
        logger.exception("Error de red reenviando webhook de Instagram a Chatwoot")

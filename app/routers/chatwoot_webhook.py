import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.config import settings
from app.security import verify_chatwoot_signature
from app.services.reply_service import process_outgoing_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/chatwoot", tags=["chatwoot"])


@router.post("/outgoing")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    body = await request.body()
    signature = request.headers.get("X-Chatwoot-Signature")
    timestamp = request.headers.get("X-Chatwoot-Timestamp")

    if not verify_chatwoot_signature(body, timestamp, signature, settings.chatwoot_inbox_webhook_secret):
        logger.warning("Firma inválida en webhook saliente de Chatwoot")
        return Response(status_code=403)

    payload = await request.json()

    if payload.get("message_type") != "outgoing":
        return Response(status_code=200)

    # Las notas privadas (incl. las que crea reply_service.py al fallar un
    # envío) también son message_type="outgoing" — sin este filtro, cada nota
    # de error dispara este mismo webhook otra vez, reintenta el envío,
    # vuelve a fallar y crea otra nota: bucle infinito.
    if payload.get("private"):
        return Response(status_code=200)

    conversation = payload.get("conversation") or {}
    if str(conversation.get("inbox_id")) != str(settings.chatwoot_inbox_id_comentarios):
        return Response(status_code=200)

    conversation_id = conversation.get("id")
    content = payload.get("content") or ""
    if conversation_id is not None and content:
        background_tasks.add_task(process_outgoing_message, conversation_id, content)

    return Response(status_code=200)

import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.config import settings
from app.security import verify_meta_signature
from app.services.comment_service import process_incoming_comment
from app.services.instagram_relay import relay_to_chatwoot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/meta", tags=["meta"])


@router.get("/instagram")
async def verify_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")

    if mode == "subscribe" and token == settings.meta_verify_token:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/instagram")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_meta_signature(body, signature, settings.meta_app_secret):
        logger.warning("Firma inválida en webhook de Meta")
        return Response(status_code=403)

    background_tasks.add_task(relay_to_chatwoot, body, signature)

    payload = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            background_tasks.add_task(process_incoming_comment, change["value"])

    return Response(status_code=200)

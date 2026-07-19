import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import get_session
from app.models import IgCommentTicket
from app.services import chatwoot_client, meta_client
from app.services.meta_client import MetaApiError

logger = logging.getLogger(__name__)

ALREADY_SENT_NOTE = (
    "Ya se envió un privado para este comentario. Si necesitas seguir hablando con esta "
    "persona, hazlo por DM normal."
)
WINDOW_EXPIRED_NOTE = (
    "Han pasado más de {days} días desde el comentario; Meta ya no permite enviar un "
    "privado para este comentario. Si el contacto ya existe por DM, contesta por ahí."
)
SEND_FAILED_NOTE = "No se pudo enviar el privado a Instagram: {error}"


async def process_outgoing_message(conversation_id: int, message_content: str) -> None:
    """Aplica los guardrails y envía el private reply a Instagram si corresponde."""
    session = get_session()
    try:
        ticket = (
            session.query(IgCommentTicket)
            .filter_by(chatwoot_conversation_id=conversation_id)
            .first()
        )
        if ticket is None:
            logger.info("Sin ticket asociado a conversation_id=%s, se ignora", conversation_id)
            return

        if ticket.reply_sent:
            logger.info("Reply ya enviado para comment_id=%s, se ignora", ticket.comment_id)
            await chatwoot_client.create_private_note(conversation_id, ALREADY_SENT_NOTE)
            return

        window = timedelta(days=settings.private_reply_window_days)
        comment_created_at = ticket.comment_created_at
        if comment_created_at and comment_created_at.tzinfo is None:
            comment_created_at = comment_created_at.replace(tzinfo=timezone.utc)
        if comment_created_at and datetime.now(timezone.utc) - comment_created_at > window:
            logger.info("Ventana de %s días expirada para comment_id=%s", window.days, ticket.comment_id)
            await chatwoot_client.create_private_note(
                conversation_id, WINDOW_EXPIRED_NOTE.format(days=settings.private_reply_window_days)
            )
            return

        try:
            await meta_client.send_private_reply(ticket.comment_id, message_content)
        except MetaApiError as exc:
            logger.exception("Error enviando private reply para comment_id=%s", ticket.comment_id)
            await chatwoot_client.create_private_note(
                conversation_id, SEND_FAILED_NOTE.format(error=exc)
            )
            return

        ticket.reply_sent = True
        ticket.reply_sent_at = datetime.now(timezone.utc)
        session.commit()

        await chatwoot_client.resolve_conversation(conversation_id)
    finally:
        session.close()

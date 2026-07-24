import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db import get_session
from app.models import IgCommentTicket
from app.services import chatwoot_client, meta_client

logger = logging.getLogger(__name__)


async def process_incoming_comment(change_value: dict) -> None:
    """Procesa un comentario raíz nuevo: enriquece, crea ticket en Chatwoot y persiste."""
    comment_id = change_value["id"]
    parent_id = change_value.get("parent_id")
    if parent_id:
        logger.info("Ignorando comentario anidado comment_id=%s parent_id=%s", comment_id, parent_id)
        return

    igsid = change_value["from"]["id"]
    username = change_value["from"].get("username")
    text = change_value.get("text", "")
    media_id = change_value["media"]["id"]

    session = get_session()
    try:
        existing = session.query(IgCommentTicket).filter_by(comment_id=comment_id).first()
        if existing:
            logger.info("Comentario duplicado ignorado comment_id=%s", comment_id)
            return

        ticket = IgCommentTicket(
            comment_id=comment_id,
            media_id=media_id,
            igsid=igsid,
            username=username,
            comment_text=text,
            comment_created_at=datetime.now(timezone.utc),
        )
        session.add(ticket)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            logger.info("Comentario duplicado (carrera) ignorado comment_id=%s", comment_id)
            return

        media = await meta_client.get_media(media_id)
        permalink = media.get("permalink")
        ticket.permalink = permalink
        session.commit()

        contact = await chatwoot_client.find_or_create_contact(igsid, username)
        contact_id = contact["id"]
        contact_inbox = next(
            (
                ci
                for ci in contact.get("contact_inboxes", [])
                if str(ci.get("inbox", {}).get("id")) == str(settings.chatwoot_inbox_id_comentarios)
            ),
            None,
        )
        if contact_inbox is None:
            raise RuntimeError(
                f"El contacto {contact_id} no tiene contact_inbox en el inbox "
                f"{settings.chatwoot_inbox_id_comentarios} (comment_id={comment_id})"
            )
        source_id = contact_inbox["source_id"]

        conversation = await chatwoot_client.create_conversation(source_id, contact_id)
        conversation_id = conversation["id"]

        message_content = (
            f"💬 Nuevo comentario de @{username or igsid}"
            + (f" en [ver publicación]({permalink})" if permalink else "")
            + f":\n\n\"{text}\""
        )
        await chatwoot_client.create_message(conversation_id, message_content)

        ticket.chatwoot_contact_id = contact_id
        ticket.chatwoot_conversation_id = conversation_id
        session.commit()
    finally:
        session.close()

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.models import IgCommentTicket
from app.services import reply_service


def _make_ticket(session_factory, **overrides) -> IgCommentTicket:
    session = session_factory()
    ticket = IgCommentTicket(
        comment_id=overrides.get("comment_id", "comment-1"),
        media_id="media-1",
        igsid="igsid-1",
        username="cliente_ejemplo",
        comment_text="Me encanta",
        chatwoot_conversation_id=overrides.get("chatwoot_conversation_id", 123),
        reply_sent=overrides.get("reply_sent", False),
        comment_created_at=overrides.get(
            "comment_created_at", datetime.now(timezone.utc)
        ),
    )
    session.add(ticket)
    session.commit()
    session.close()
    return ticket


@pytest.mark.asyncio
async def test_already_sent_does_not_call_meta_again(db_session_factory, monkeypatch):
    _make_ticket(db_session_factory, reply_sent=True)

    send_reply_mock = AsyncMock()
    note_mock = AsyncMock()
    monkeypatch.setattr(reply_service.meta_client, "send_private_reply", send_reply_mock)
    monkeypatch.setattr(reply_service.chatwoot_client, "create_private_note", note_mock)

    await reply_service.process_outgoing_message(123, "segunda respuesta")

    send_reply_mock.assert_not_called()
    note_mock.assert_awaited_once()
    assert reply_service.ALREADY_SENT_NOTE in note_mock.call_args.args[1]


@pytest.mark.asyncio
async def test_window_expired_does_not_call_meta(db_session_factory, monkeypatch):
    old_date = datetime.now(timezone.utc) - timedelta(days=8)
    _make_ticket(db_session_factory, comment_created_at=old_date)

    send_reply_mock = AsyncMock()
    note_mock = AsyncMock()
    monkeypatch.setattr(reply_service.meta_client, "send_private_reply", send_reply_mock)
    monkeypatch.setattr(reply_service.chatwoot_client, "create_private_note", note_mock)

    await reply_service.process_outgoing_message(123, "respuesta tardía")

    send_reply_mock.assert_not_called()
    note_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_successful_reply_marks_sent_and_resolves(db_session_factory, monkeypatch):
    _make_ticket(db_session_factory)

    send_reply_mock = AsyncMock(return_value={"id": "reply-1"})
    resolve_mock = AsyncMock()
    monkeypatch.setattr(reply_service.meta_client, "send_private_reply", send_reply_mock)
    monkeypatch.setattr(reply_service.chatwoot_client, "resolve_conversation", resolve_mock)

    await reply_service.process_outgoing_message(123, "¡Sí, quedan plazas!")

    send_reply_mock.assert_awaited_once_with("comment-1", "¡Sí, quedan plazas!")
    resolve_mock.assert_awaited_once_with(123)

    session = db_session_factory()
    ticket = session.query(IgCommentTicket).filter_by(comment_id="comment-1").first()
    assert ticket.reply_sent is True
    assert ticket.reply_sent_at is not None
    session.close()


@pytest.mark.asyncio
async def test_no_ticket_for_conversation_is_ignored(db_session_factory, monkeypatch):
    send_reply_mock = AsyncMock()
    monkeypatch.setattr(reply_service.meta_client, "send_private_reply", send_reply_mock)

    await reply_service.process_outgoing_message(999, "hola")

    send_reply_mock.assert_not_called()

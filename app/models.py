from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class IgCommentTicket(Base):
    __tablename__ = "ig_comment_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    media_id: Mapped[str] = mapped_column(String, nullable=False)
    igsid: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    permalink: Mapped[str | None] = mapped_column(String, nullable=True)
    comment_text: Mapped[str | None] = mapped_column(String, nullable=True)

    chatwoot_contact_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chatwoot_conversation_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )

    reply_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reply_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    comment_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

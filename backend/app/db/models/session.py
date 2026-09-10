from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.db.models.user import User


class RefreshToken(Base):
    """Secure session tracking for refresh tokens.
    Never stores plaintext tokens; only SHA-256 digests of high-entropy random secrets.
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
    )

    @property
    def is_active(self) -> bool:
        """Determines if the refresh session is currently valid."""
        return self.revoked_at is None and datetime.now(self.expires_at.tzinfo) < self.expires_at

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} active={self.is_active}>"

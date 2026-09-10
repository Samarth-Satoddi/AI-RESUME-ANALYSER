from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class Profile(Base, TimestampMixin):
    """User career profile and professional metadata."""
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    github_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    portfolio_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    target_role: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    years_of_experience: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )

    def __repr__(self) -> str:
        return f"<Profile id={self.id} user_id={self.user_id} full_name={self.full_name}>"

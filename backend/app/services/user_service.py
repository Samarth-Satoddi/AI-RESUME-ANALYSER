from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models import User
from app.schemas.user import UserUpdateRequest


class UserService:
    """Operations for user account identity."""

    @staticmethod
    def get_user_by_id(db: Session, user_id) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(detail="User not found.")
        return user

    @staticmethod
    def update_user_me(db: Session, user: User, data: UserUpdateRequest) -> User:
        """Update user account fields with validation."""
        if data.email is not None:
            normalized_email = data.email.strip().lower()
            if normalized_email != user.email:
                existing = db.query(User).filter(User.email == normalized_email).first()
                if existing:
                    raise BadRequestError(detail="An account with this email already exists.")
                user.email = normalized_email

        db.commit()
        db.refresh(user)
        return user

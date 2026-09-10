from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models import Profile, User
from app.schemas.profile import ProfileUpdateRequest


class ProfileService:
    """Business operations for user career profiles."""

    @staticmethod
    def get_profile_by_user(db: Session, user: User) -> Profile:
        """Fetch career profile for the authenticated user, creating one if absent."""
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not profile:
            profile = Profile(
                user_id=user.id,
                full_name=user.email.split("@")[0].capitalize(),
                years_of_experience=0.0,
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @staticmethod
    def update_profile(db: Session, user: User, data: ProfileUpdateRequest) -> Profile:
        """Update candidate profile attributes."""
        profile = ProfileService.get_profile_by_user(db, user)

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(profile, field, value)

        db.commit()
        db.refresh(profile)
        return profile

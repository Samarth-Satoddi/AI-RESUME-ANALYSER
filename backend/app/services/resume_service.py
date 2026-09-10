from typing import List, Optional
import uuid
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationException
from app.core.logging import logger
from app.db.models import Resume, ResumeVersion, ResumeSection, User
from app.schemas.resume import (
    ResumeResponse,
    ResumeSectionResponse,
    ResumeSectionsListResponse,
    ResumeTextResponse,
)
from app.services.file_validator import FileValidator
from app.services.storage_service import StorageService
from app.services.text_extractor import TextExtractor
from app.services.section_detector import SectionDetector


class ResumeService:
    """Service layer managing resume document persistence, versioning, and lifecycle."""

    @staticmethod
    def to_response_dto(resume: Resume) -> ResumeResponse:
        """Transform a Resume ORM model into a safe ResumeResponse schema."""
        # Retrieve primary version info
        active_version = resume.versions[-1] if resume.versions else None
        version_num = active_version.version_number if active_version else 1
        parser_status = active_version.parser_status if active_version else "pending"

        return ResumeResponse(
            id=resume.id,
            name=resume.name,
            original_filename=resume.original_filename,
            file_type=resume.file_type,
            file_size=resume.file_size,
            is_primary=resume.is_primary,
            version_number=version_num,
            parser_status=parser_status,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )

    @classmethod
    async def upload_resume(
        cls,
        db: Session,
        user: User,
        file: UploadFile,
        custom_name: Optional[str] = None,
    ) -> ResumeResponse:
        """Process multipart upload, validate integrity, store on disk, and create DB records."""
        logger.info(f"resume_upload_started for user={user.id}, file={file.filename}")

        # Stream & validate file onto disk
        stored_filename, file_size, sanitized_name, file_type = await StorageService.save_upload_file(file)

        # Determine display name
        display_name = custom_name.strip() if custom_name and custom_name.strip() else FileValidator.generate_display_name(sanitized_name)

        # Determine primary status (first upload defaults to primary)
        existing_count = db.query(Resume).filter(Resume.user_id == user.id).count()
        is_primary = (existing_count == 0)

        new_resume = Resume(
            user_id=user.id,
            name=display_name,
            original_filename=sanitized_name,
            file_type=file_type,
            file_size=file_size,
            storage_path=stored_filename,
            is_primary=is_primary,
        )

        try:
            db.add(new_resume)
            db.flush()  # Obtain new_resume.id

            # Create initial version 1
            version_1 = ResumeVersion(
                resume_id=new_resume.id,
                version_number=1,
                extracted_text=None,
                parser_status="pending",
            )
            db.add(version_1)
            db.flush()

            # Attempt immediate text extraction and section detection
            try:
                file_path = StorageService.get_file_path(stored_filename)
                extracted_text = TextExtractor.extract(file_path, file_type)
                version_1.extracted_text = extracted_text
                version_1.parser_status = "completed"

                detector = SectionDetector()
                sections = detector.detect_sections(extracted_text)
                for sec in sections:
                    new_sec = ResumeSection(
                        resume_version_id=version_1.id,
                        section_type=sec.section_type,
                        content=sec.content,
                        section_order=sec.section_order,
                    )
                    db.add(new_sec)
                logger.info(f"resume_sections_detected count={len(sections)} resume_id={new_resume.id}")
            except Exception as parse_err:
                version_1.parser_status = "failed"
                logger.warning(f"resume_initial_parse_failed resume_id={new_resume.id}: {str(parse_err)}")

            db.commit()
            db.refresh(new_resume)

            logger.info(f"resume_upload_success resume_id={new_resume.id} for user={user.id}")
            return cls.to_response_dto(new_resume)

        except Exception as exc:
            db.rollback()
            # Clean up stored file to prevent orphaned storage on database failure
            StorageService.delete_file(stored_filename)
            logger.error(f"resume_upload_failed for user={user.id}: {str(exc)}")
            raise

    @classmethod
    def parse_resume(cls, db: Session, user: User, resume_id: uuid.UUID) -> ResumeSectionsListResponse:
        """Manually trigger text extraction and section detection for a resume."""
        resume = cls.get_resume(db, user, resume_id)
        active_version = resume.versions[-1] if resume.versions else None
        if not active_version:
            raise NotFoundError("No active resume version found.")

        file_path = StorageService.get_file_path(resume.storage_path)

        try:
            # 1. Extract & normalize text
            extracted_text = TextExtractor.extract(file_path, resume.file_type)
            active_version.extracted_text = extracted_text

            # 2. Detect sections
            detector = SectionDetector()
            detected_sections = detector.detect_sections(extracted_text)

            # 3. Remove previous sections for this version
            db.query(ResumeSection).filter(ResumeSection.resume_version_id == active_version.id).delete()

            # 4. Insert new sections
            created_sections: List[ResumeSection] = []
            for sec in detected_sections:
                new_sec = ResumeSection(
                    resume_version_id=active_version.id,
                    section_type=sec.section_type,
                    content=sec.content,
                    section_order=sec.section_order,
                )
                db.add(new_sec)
                created_sections.append(new_sec)

            active_version.parser_status = "completed"
            db.commit()
            db.refresh(active_version)

            logger.info(f"resume_reparsed_successfully resume_id={resume_id} sections={len(created_sections)}")

            return ResumeSectionsListResponse(
                resume_id=resume.id,
                version_number=active_version.version_number,
                parser_status=active_version.parser_status,
                total_sections=len(created_sections),
                sections=[ResumeSectionResponse.model_validate(s) for s in created_sections],
            )
        except Exception as exc:
            active_version.parser_status = "failed"
            db.commit()
            logger.error(f"resume_parse_error resume_id={resume_id}: {str(exc)}")
            raise ValidationException(f"Failed to parse resume: {str(exc)}")

    @classmethod
    def get_resume_sections(cls, db: Session, user: User, resume_id: uuid.UUID) -> ResumeSectionsListResponse:
        """Fetch all detected sections for candidate's resume version."""
        resume = cls.get_resume(db, user, resume_id)
        active_version = resume.versions[-1] if resume.versions else None
        if not active_version:
            raise NotFoundError("No active resume version found.")

        # If sections haven't been parsed yet but text can be parsed, auto-parse
        sections = (
            db.query(ResumeSection)
            .filter(ResumeSection.resume_version_id == active_version.id)
            .order_by(ResumeSection.section_order.asc())
            .all()
        )

        if not sections and active_version.parser_status == "pending":
            return cls.parse_resume(db, user, resume_id)

        return ResumeSectionsListResponse(
            resume_id=resume.id,
            version_number=active_version.version_number,
            parser_status=active_version.parser_status,
            total_sections=len(sections),
            sections=[ResumeSectionResponse.model_validate(s) for s in sections],
        )

    @classmethod
    def get_resume_text(cls, db: Session, user: User, resume_id: uuid.UUID) -> ResumeTextResponse:
        """Fetch extracted text and parser status for candidate's resume."""
        resume = cls.get_resume(db, user, resume_id)
        active_version = resume.versions[-1] if resume.versions else None
        if not active_version:
            raise NotFoundError("No active resume version found.")

        # If pending, attempt extraction
        if active_version.parser_status == "pending" or not active_version.extracted_text:
            try:
                file_path = StorageService.get_file_path(resume.storage_path)
                active_version.extracted_text = TextExtractor.extract(file_path, resume.file_type)
                active_version.parser_status = "completed"
                db.commit()
                db.refresh(active_version)
            except Exception:
                pass

        return ResumeTextResponse(
            resume_id=resume.id,
            version_number=active_version.version_number,
            parser_status=active_version.parser_status,
            extracted_text=active_version.extracted_text,
        )


    @classmethod
    def list_resumes(cls, db: Session, user: User) -> List[ResumeResponse]:
        """List all resumes belonging strictly to the authenticated user."""
        resumes = (
            db.query(Resume)
            .filter(Resume.user_id == user.id)
            .order_by(Resume.created_at.desc())
            .all()
        )
        return [cls.to_response_dto(r) for r in resumes]

    @classmethod
    def get_resume(cls, db: Session, user: User, resume_id: uuid.UUID) -> Resume:
        """Fetch a specific resume, enforcing strict ownership."""
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == user.id)
            .first()
        )
        if not resume:
            raise NotFoundError(detail="Resume not found or permission denied.")
        return resume

    @classmethod
    def set_primary_resume(cls, db: Session, user: User, resume_id: uuid.UUID) -> ResumeResponse:
        """Atomically set a resume as primary, unsetting any previous primary resume."""
        target = cls.get_resume(db, user, resume_id)

        # Unset all other resumes for this user
        db.query(Resume).filter(
            Resume.user_id == user.id,
            Resume.id != resume_id,
        ).update({"is_primary": False})

        target.is_primary = True
        db.commit()
        db.refresh(target)
        logger.info(f"resume_set_primary resume_id={target.id} user={user.id}")
        return cls.to_response_dto(target)

    @classmethod
    def update_resume_name(
        cls,
        db: Session,
        user: User,
        resume_id: uuid.UUID,
        new_name: str,
    ) -> ResumeResponse:
        """Rename an existing resume."""
        target = cls.get_resume(db, user, resume_id)
        target.name = new_name.strip()
        db.commit()
        db.refresh(target)
        return cls.to_response_dto(target)

    @classmethod
    def delete_resume(cls, db: Session, user: User, resume_id: uuid.UUID) -> None:
        """Delete a resume from database and remove its physical file from disk."""
        target = cls.get_resume(db, user, resume_id)
        stored_file = target.storage_path
        was_primary = target.is_primary

        db.delete(target)
        db.commit()

        # Remove physical file
        StorageService.delete_file(stored_file)
        logger.info(f"resume_deleted resume_id={resume_id} user={user.id}")

        # If deleted resume was primary, designate the most recent remaining resume as primary
        if was_primary:
            next_resume = (
                db.query(Resume)
                .filter(Resume.user_id == user.id)
                .order_by(Resume.created_at.desc())
                .first()
            )
            if next_resume:
                next_resume.is_primary = True
                db.commit()

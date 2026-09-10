import re
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import Certification, Education, Experience, Project, ResumeVersion, ResumeSection


class ExtractedContact(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class ExtractedExperience(BaseModel):
    company: str
    job_title: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None


class ExtractedEducation(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade: Optional[str] = None


class ExtractedProject(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: Optional[List[str]] = None
    project_url: Optional[str] = None
    github_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ExtractedCertification(BaseModel):
    name: str
    issuing_organization: str
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None


class EntityExtractor:
    """
    Pattern and heuristic entity extraction service for resumes.
    Parses contact details, work experiences, education history,
    projects, and certifications from segmented sections and raw text.
    """

    # Common email regex
    EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

    # International and North American phone regex
    PHONE_REGEX = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

    # LinkedIn and GitHub regexes
    LINKEDIN_REGEX = r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+"
    GITHUB_REGEX = r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+"
    URL_REGEX = r"https?://[^\s/$.?#].[^\s]*"

    # Common date formats (e.g., 'Jan 2020 - Present', '2018 - 2022', '06/2019 - 08/2021')
    DATE_RANGE_REGEX = r"(?P<start>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}/\d{4}|\d{4})\s*(?:-|–|—|to)\s*(?P<end>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}/\d{4}|\d{4}|Present|Current|Now)"

    # Degrees keywords
    DEGREE_KEYWORDS = [
        "Bachelor of Science", "Bachelor of Arts", "B.S.", "B.A.", "BS", "BA",
        "Master of Science", "Master of Arts", "M.S.", "M.A.", "MS", "MA",
        "Master of Business Administration", "MBA", "Ph.D.", "PhD", "Doctorate",
        "Associate of Science", "Associate Degree", "B.Tech", "B.E.", "M.Tech"
    ]

    def extract_contact_info(self, text: str) -> ExtractedContact:
        """Extract candidate contact metadata."""
        contact = ExtractedContact()

        email_match = re.search(self.EMAIL_REGEX, text)
        if email_match:
            contact.email = email_match.group(0).strip()

        phone_match = re.search(self.PHONE_REGEX, text)
        if phone_match:
            contact.phone = phone_match.group(0).strip()

        linkedin_match = re.search(self.LINKEDIN_REGEX, text, re.IGNORECASE)
        if linkedin_match:
            contact.linkedin_url = linkedin_match.group(0).strip()

        github_match = re.search(self.GITHUB_REGEX, text, re.IGNORECASE)
        if github_match:
            contact.github_url = github_match.group(0).strip()

        # Name heuristic: First non-empty line before email or phone
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            first_line = lines[0]
            # Ensure first line looks like a name (not an email or long paragraph)
            if len(first_line) < 40 and not re.search(self.EMAIL_REGEX, first_line) and not first_line.startswith("http"):
                contact.name = first_line

        # Location heuristic: search for 'City, State' or 'City, Country' in header parts
        for line in lines[:5]:
            chunks = re.split(r"[|•·]", line)
            for chunk in chunks:
                chunk_s = chunk.strip()
                if re.search(self.EMAIL_REGEX, chunk_s) or re.search(self.PHONE_REGEX, chunk_s) or "http" in chunk_s:
                    continue
                loc_match = re.search(r"([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}|[A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z]+)", chunk_s)
                if loc_match:
                    contact.location = loc_match.group(0).strip()
                    break
            if contact.location:
                break

        return contact


    def extract_experiences(self, section_content: str) -> List[ExtractedExperience]:
        """Parse work experiences from the experience section content."""
        if not section_content:
            return []

        experiences: List[ExtractedExperience] = []
        blocks = re.split(r"\n\s*\n", section_content)

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue

            # Check for date range in block
            date_match = re.search(self.DATE_RANGE_REGEX, block, re.IGNORECASE)
            start_date = date_match.group("start") if date_match else None
            end_date = date_match.group("end") if date_match else None
            is_current = bool(end_date and end_date.lower() in ("present", "current", "now"))

            # First line usually contains Title and/or Company
            first_line = lines[0]
            parts = [p.strip() for p in re.split(r"[|\-–—•@,]", first_line) if p.strip()]

            if len(parts) >= 2:
                job_title = parts[0]
                company = parts[1]
            elif len(parts) == 1:
                job_title = parts[0]
                company = lines[1] if len(lines) > 1 and len(lines[1]) < 50 else "Company"
            else:
                continue

            description_lines = lines[1:]
            description = "\n".join(description_lines) if description_lines else None

            experiences.append(
                ExtractedExperience(
                    company=company,
                    job_title=job_title,
                    start_date=start_date,
                    end_date=end_date,
                    is_current=is_current,
                    description=description,
                )
            )

        # Fallback: if no blocks split cleanly, treat whole section as one experience
        if not experiences and len(section_content) > 20:
            lines = [l.strip() for l in section_content.split("\n") if l.strip()]
            experiences.append(
                ExtractedExperience(
                    company="Professional Experience",
                    job_title=lines[0] if lines else "Engineer",
                    description=section_content,
                )
            )

        return experiences

    def extract_education(self, section_content: str) -> List[ExtractedEducation]:
        """Parse educational background from education section."""
        if not section_content:
            return []

        education_list: List[ExtractedEducation] = []
        blocks = re.split(r"\n\s*\n", section_content)

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue

            # Detect degree
            detected_degree = "Degree"
            for deg in self.DEGREE_KEYWORDS:
                if re.search(rf"\b{re.escape(deg)}\b", block, re.IGNORECASE):
                    detected_degree = deg
                    break

            # Detect GPA/Grade
            gpa_match = re.search(r"(?:GPA|Grade|CGPA)[:\s]*([0-9\.]+(?:\s*/\s*[0-9\.]+)?)", block, re.IGNORECASE)
            grade = gpa_match.group(1) if gpa_match else None

            # Detect dates
            date_match = re.search(self.DATE_RANGE_REGEX, block, re.IGNORECASE)
            start_date = date_match.group("start") if date_match else None
            end_date = date_match.group("end") if date_match else None

            # Institution heuristic
            institution = lines[0]
            if any(deg.lower() in institution.lower() for deg in self.DEGREE_KEYWORDS) and len(lines) > 1:
                detected_degree = lines[0]
                institution = lines[1]

            education_list.append(
                ExtractedEducation(
                    institution=institution,
                    degree=detected_degree,
                    field_of_study="Computer Science / Engineering",
                    start_date=start_date,
                    end_date=end_date,
                    grade=grade,
                )
            )

        return education_list

    def extract_projects(self, section_content: str) -> List[ExtractedProject]:
        """Parse portfolio and technical projects."""
        if not section_content:
            return []

        projects: List[ExtractedProject] = []
        blocks = re.split(r"\n\s*\n", section_content)

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue

            name = lines[0].split("|")[0].split("-")[0].strip()
            github_match = re.search(self.GITHUB_REGEX, block)
            github_url = github_match.group(0) if github_match else None

            desc = "\n".join(lines[1:]) if len(lines) > 1 else lines[0]

            projects.append(
                ExtractedProject(
                    name=name,
                    description=desc,
                    github_url=github_url,
                )
            )

        return projects

    def extract_certifications(self, section_content: str) -> List[ExtractedCertification]:
        """Parse professional licenses and certifications."""
        if not section_content:
            return []

        certs: List[ExtractedCertification] = []
        lines = [l.strip() for l in section_content.split("\n") if l.strip()]

        for line in lines:
            # Clean bullet marks
            cleaned = re.sub(r"^[-*•]\s*", "", line)
            if len(cleaned) < 3:
                continue

            parts = [p.strip() for p in cleaned.split(" - ") if p.strip()]
            name = parts[0]
            org = parts[1] if len(parts) > 1 else "Professional Body"

            certs.append(
                ExtractedCertification(
                    name=name,
                    issuing_organization=org,
                )
            )

        return certs

    def process_and_save_entities(
        self,
        db: Session,
        resume_version: ResumeVersion,
        sections: List[ResumeSection],
        full_text: str,
    ) -> Dict[str, int]:
        """
        Extract all entities across sections and persist them into Experience,
        Education, Project, and Certification tables with cascade replacement.
        """
        # Group section content by section_type
        section_map: Dict[str, str] = {}
        for s in sections:
            section_map[s.section_type] = s.content

        # 1. Experiences
        exp_content = section_map.get("experience", "")
        extracted_exps = self.extract_experiences(exp_content)
        db.query(Experience).filter(Experience.resume_version_id == resume_version.id).delete()
        for e in extracted_exps:
            rec = Experience(
                resume_version_id=resume_version.id,
                company=e.company,
                job_title=e.job_title,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                is_current=e.is_current,
                description=e.description,
            )
            db.add(rec)

        # 2. Education
        edu_content = section_map.get("education", "")
        extracted_edus = self.extract_education(edu_content)
        db.query(Education).filter(Education.resume_version_id == resume_version.id).delete()
        for edu in extracted_edus:
            rec = Education(
                resume_version_id=resume_version.id,
                institution=edu.institution,
                degree=edu.degree,
                field_of_study=edu.field_of_study,
                start_date=edu.start_date,
                end_date=edu.end_date,
                grade=edu.grade,
            )
            db.add(rec)

        # 3. Projects
        proj_content = section_map.get("projects", "")
        extracted_projs = self.extract_projects(proj_content)
        db.query(Project).filter(Project.resume_version_id == resume_version.id).delete()
        for p in extracted_projs:
            rec = Project(
                resume_version_id=resume_version.id,
                name=p.name,
                description=p.description,
                github_url=p.github_url,
            )
            db.add(rec)

        # 4. Certifications
        cert_content = section_map.get("certifications", "")
        extracted_certs = self.extract_certifications(cert_content)
        db.query(Certification).filter(Certification.resume_version_id == resume_version.id).delete()
        for c in extracted_certs:
            rec = Certification(
                resume_version_id=resume_version.id,
                name=c.name,
                issuing_organization=c.issuing_organization,
                issue_date=c.issue_date,
            )
            db.add(rec)

        db.commit()

        counts = {
            "experiences": len(extracted_exps),
            "education": len(extracted_edus),
            "projects": len(extracted_projs),
            "certifications": len(extracted_certs),
        }
        logger.info(f"Entities processed for resume_version={resume_version.id}: {counts}")
        return counts

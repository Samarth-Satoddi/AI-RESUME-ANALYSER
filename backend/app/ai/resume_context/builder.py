import uuid
import re
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.db.models.resume import Resume, ResumeVersion, ResumeSection, ResumeSkill, Experience, Education, Project
from app.db.models.analysis import Analysis, MissingSkill, SkillMatch, Recommendation
from app.db.models.job import JobDescription
from app.ai.intent.classifier import AssistantIntent
from app.core.logging import logger


class ResumeContextBuilder:
    """
    Constructs accurate, structured, token-efficient context for the LLM assistant
    using verified database records. Never invents facts or metrics.
    """

    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def get_verified_resume(self, resume_id: uuid.UUID) -> Optional[Resume]:
        """Ensures the resume exists and belongs strictly to the authenticated user."""
        return self.db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == self.user_id,
        ).first()

    def get_latest_version(self, resume_id: uuid.UUID) -> Optional[ResumeVersion]:
        return self.db.query(ResumeVersion).filter(
            ResumeVersion.resume_id == resume_id,
        ).order_by(ResumeVersion.version_number.desc()).first()

    def get_latest_analysis(self, resume_version_id: uuid.UUID, job_id: Optional[uuid.UUID] = None) -> Optional[Analysis]:
        query = self.db.query(Analysis).filter(
            Analysis.resume_version_id == resume_version_id,
            Analysis.user_id == self.user_id,
            Analysis.status == "completed",
        )
        if job_id:
            query = query.filter(Analysis.job_description_id == job_id)
        return query.order_by(Analysis.created_at.desc()).first()

    def _parse_candidate_name(self, raw_text: Optional[str], default_name: str) -> str:
        """Extracts the candidate name from the top of the resume text if present."""
        if not raw_text:
            return default_name
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        if lines:
            first_line = lines[0]
            # If the first line looks like a person's name (not a section header)
            if len(first_line) < 60 and not any(h in first_line.lower() for h in ("summary", "resume", "curriculum", "cv", "skills")):
                return first_line
        return default_name

    def _parse_projects_from_text(self, projects_text: str, projects_db: List[Project]) -> List[Dict[str, Any]]:
        """Parses individual projects and their bullet achievements/metrics from raw text and DB."""
        projects_list = []

        # If DB already has clean distinct projects
        if len(projects_db) > 1:
            for p in projects_db:
                metrics = re.findall(r"(?:~?\d+%(?:\s+[\w\s-]+)?|\b\d+x\b)", p.description or "")
                projects_list.append({
                    "name": p.name.rstrip(":"),
                    "description": p.description or "",
                    "technologies": p.technologies or [],
                    "metrics": metrics,
                })
            return projects_list

        # Otherwise parse distinct projects from section text (e.g., "Healthcare Assistant:", "Personal Smart Assistant:")
        content = projects_text or (projects_db[0].description if projects_db else "")
        if not content:
            return []

        # Regex split on project headers like "Project Name:" or "### Project Name"
        chunks = re.split(r"\n(?=[A-Z][A-Za-z0-9\s-]{2,40}:)", "\n" + content)
        for chunk in chunks:
            clean_chunk = chunk.strip()
            if not clean_chunk:
                continue
            lines = clean_chunk.split("\n")
            header = lines[0].strip().rstrip(":")
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else clean_chunk
            metrics = re.findall(r"(?:~?\d+%(?:\s+[\w\s-]+)?|\b\d+x\b)", clean_chunk)
            projects_list.append({
                "name": header,
                "description": body,
                "metrics": metrics,
            })

        return projects_list if projects_list else [{"name": "Academic Projects", "description": content, "metrics": []}]

    def build_context(
        self,
        resume_id: uuid.UUID,
        intent: AssistantIntent,
        job_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Builds targeted context payload based on user intent and verified database records.
        """
        resume = self.get_verified_resume(resume_id)
        if not resume:
            raise ValueError(f"Resume {resume_id} not found or access denied for this user.")

        version = self.get_latest_version(resume.id)
        if not version:
            raise ValueError(f"Resume version not found for resume {resume_id}.")

        # Pull verified entities from database
        skills_db = self.db.query(ResumeSkill).filter(ResumeSkill.resume_version_id == version.id).all()
        sections_db = self.db.query(ResumeSection).filter(ResumeSection.resume_version_id == version.id).order_by(ResumeSection.section_order).all()
        experiences_db = self.db.query(Experience).filter(Experience.resume_version_id == version.id).all()
        education_db = self.db.query(Education).filter(Education.resume_version_id == version.id).all()
        projects_db = self.db.query(Project).filter(Project.resume_version_id == version.id).all()

        analysis = self.get_latest_analysis(version.id, job_id)

        # Section dictionary
        section_dict = {sec.section_type.lower(): sec.content.strip() for sec in sections_db if sec.content}

        # Candidate identity
        candidate_name = self._parse_candidate_name(version.extracted_text, resume.name)

        # Verified skills from database + taxonomy
        db_skill_names = [s.skill_name for s in skills_db]

        # Extract structured skills from raw skills section text if present
        raw_skills_text = section_dict.get("skills", "")
        extracted_skills_list = list(db_skill_names)

        # Merge any explicit skills listed in the raw skills section (e.g. CrewAI, RAG, ChromaDB)
        if raw_skills_text:
            found_skills = re.findall(r"\b(?:Python|Java|LLMs|RAG|LangChain|CrewAI|ChromaDB|Git|GitHub|Docker|Kubernetes|AWS|React|TypeScript|Node\.js|Next\.js|PostgreSQL|MySQL|MongoDB|FastAPI|Flask|Spring Boot)\b", raw_skills_text, re.IGNORECASE)
            for fs in found_skills:
                # Add if not already present (case-insensitive)
                if not any(fs.lower() == s.lower() for s in extracted_skills_list):
                    extracted_skills_list.append(fs)

        # Work Experience summary
        experience_entries = []
        for exp in experiences_db:
            dates = f"{exp.start_date or ''} - {'Present' if exp.is_current else (exp.end_date or '')}".strip(" -")
            exp_text = f"• {exp.job_title} at {exp.company} ({dates})"
            if exp.description:
                exp_text += f"\n  {exp.description}"
            experience_entries.append(exp_text)

        # Education summary
        education_entries = []
        if section_dict.get("education"):
            education_entries = [f"• {line.strip()}" for line in section_dict["education"].split("\n") if line.strip()]
        elif education_db:
            for edu in education_db:
                dates = f"{edu.start_date or ''} - {edu.end_date or ''}".strip(" -")
                field = f" in {edu.field_of_study}" if edu.field_of_study else ""
                education_entries.append(f"• {edu.degree}{field}, {edu.institution} ({dates})")

        # Project summary
        parsed_projects = self._parse_projects_from_text(section_dict.get("projects", ""), projects_db)

        # Certifications summary
        certifications_entries = []
        if section_dict.get("certifications"):
            certifications_entries = [f"• {line.strip()}" for line in section_dict["certifications"].split("\n") if line.strip()]

        # Analysis context if available
        analysis_context = {}
        if analysis:
            missing_skills = [m.skill_name for m in analysis.missing_skills]
            matched_skills = [m.skill_name for m in analysis.skill_matches if m.match_type in ("exact", "semantic")]
            recs = [f"- {r.title}: {r.description}" for r in analysis.recommendations]

            analysis_context = {
                "overall_score": analysis.overall_score,
                "ats_score": analysis.ats_score,
                "resume_score": analysis.resume_score,
                "skill_score": analysis.skill_score,
                "semantic_score": analysis.semantic_score,
                "missing_skills": missing_skills,
                "matched_skills": matched_skills,
                "recommendations": recs,
            }

        # Target job context if available
        job_context = {}
        target_job = None
        if job_id:
            target_job = self.db.query(JobDescription).filter(JobDescription.id == job_id).first()
        elif analysis and analysis.job_description:
            target_job = analysis.job_description

        if target_job:
            req_skills = []
            if hasattr(target_job, "requirements") and target_job.requirements:
                req_skills = [r.normalized_skill_name for r in target_job.requirements]
            job_context = {
                "title": target_job.title,
                "company": target_job.company,
                "required_skills": req_skills,
            }

        # Build structured JSON payload
        structured_payload = {
            "candidate_name": candidate_name,
            "resume_id": str(resume.id),
            "professional_summary": section_dict.get("summary", "None provided"),
            "verified_skills": extracted_skills_list,
            "skills_raw_breakdown": section_dict.get("skills", ", ".join(extracted_skills_list)),
            "professional_work_experience": experience_entries,
            "academic_and_personal_projects": parsed_projects,
            "education": education_entries,
            "certifications": certifications_entries,
            "deterministic_analysis": analysis_context if analysis else None,
            "target_job": job_context if job_context else None,
        }

        # Safe audit log (DO NOT print phone number or email)
        logger.info(
            f"Resume Context Safe Summary:\n"
            f"  resume_id: {resume.id}\n"
            f"  candidate_name: {candidate_name}\n"
            f"  version_id: {version.id}\n"
            f"  summary_present: {bool(section_dict.get('summary'))}\n"
            f"  skills: {', '.join(extracted_skills_list)}\n"
            f"  projects: {', '.join([p['name'] for p in parsed_projects])}\n"
            f"  experience_count: {len(experience_entries)}\n"
            f"  education_count: {len(education_entries)}\n"
            f"  certifications_count: {len(certifications_entries)}"
        )

        # Format context text targeted by intent
        formatted_prompt_context = self._format_prompt_context(
            intent=intent,
            payload=structured_payload,
        )

        return {
            "resume_id": str(resume.id),
            "resume_name": resume.name,
            "candidate_name": candidate_name,
            "version_number": version.version_number,
            "skills": extracted_skills_list,
            "has_analysis": analysis is not None,
            "analysis": analysis_context,
            "job": job_context,
            "structured_payload": structured_payload,
            "formatted_context": formatted_prompt_context,
        }

    def _format_prompt_context(
        self,
        intent: AssistantIntent,
        payload: Dict[str, Any],
    ) -> str:
        """Constructs concise, relevant text blocks for the system/user prompt."""
        candidate_name = payload["candidate_name"]
        lines = [
            f"=== VERIFIED RESUME CONTEXT: {candidate_name} ===",
            "CRITICAL GROUNDING NOTICE: The information below is the ONLY factual data that exists for this candidate. "
            "Do NOT invent employers, job titles, years of experience, or skills not explicitly listed below.\n",
        ]

        # Professional Summary
        summary = payload.get("professional_summary")
        if summary and summary != "None provided":
            lines.append(f"[PROFESSIONAL SUMMARY]\n{summary}\n")

        # Verified Skills
        skills = payload.get("verified_skills", [])
        skills_raw = payload.get("skills_raw_breakdown", "")
        lines.append("[VERIFIED SKILLS FROM RESUME]")
        if skills_raw:
            lines.append(skills_raw)
        elif skills:
            lines.append(", ".join(skills))
        else:
            lines.append("None explicitly listed.")
        lines.append("RULE: Only the above skills exist on this resume. Do NOT assume, extrapolate, or claim any unlisted skill.\n")

        # Professional Work Experience
        experiences = payload.get("professional_work_experience", [])
        lines.append("[PROFESSIONAL WORK EXPERIENCE]")
        if experiences:
            lines.extend(experiences)
        else:
            lines.append("NONE LISTED. The candidate has ZERO listed formal employment records or employers.")
            lines.append("RULE: The candidate has no listed professional work experience. Do NOT invent companies, job titles, or years of experience. State clearly that the candidate currently lists no professional work experience.")
        lines.append("")

        # Projects & Achievements
        projects = payload.get("academic_and_personal_projects", [])
        lines.append("[PROJECTS & ACHIEVEMENTS]")
        if projects:
            for p in projects:
                lines.append(f"• Project: {p['name']}")
                if p.get("description"):
                    lines.append(f"  {p['description']}")
                if p.get("metrics"):
                    lines.append(f"  Real Project Metrics: {', '.join(p['metrics'])}")
        else:
            lines.append("None explicitly listed.")
        lines.append("")

        # Education
        education = payload.get("education", [])
        lines.append("[EDUCATION]")
        if education:
            lines.extend(education)
        else:
            lines.append("None listed.")
        lines.append("")

        # Certifications
        certifications = payload.get("certifications", [])
        if certifications:
            lines.append("[CERTIFICATIONS & ACHIEVEMENTS]")
            lines.extend(certifications)
            lines.append("")

        # Analysis Summary
        analysis = payload.get("deterministic_analysis")
        if analysis:
            lines.append(f"[DETERMINISTIC ANALYSIS SUMMARY]: ATS Score: {analysis.get('ats_score', 'N/A')}/100, Overall Score: {analysis.get('overall_score', 'N/A')}/100")
            if analysis.get("missing_skills"):
                lines.append(f"Identified Skill Gaps: {', '.join(analysis['missing_skills'][:6])}")
            if analysis.get("recommendations"):
                lines.append("Deterministic Recommendations:\n" + "\n".join(analysis["recommendations"][:3]))
            lines.append("")

        # Target Job Context
        job = payload.get("target_job")
        if job:
            lines.append(f"[TARGET BENCHMARK JOB]: {job.get('title')} at {job.get('company', 'Unknown')}")
            if job.get("required_skills"):
                lines.append(f"Job Required Skills: {', '.join(job['required_skills'])}")
            lines.append("")

        return "\n".join(lines)

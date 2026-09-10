import re
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel


class DetectedSection(BaseModel):
    """Structured representation of a detected resume section."""
    section_type: str
    raw_heading: str
    content: str
    section_order: int
    confidence: float = 1.0


class SectionDetector:
    """
    Heuristic, rule-based Resume Section Detection Engine.
    Detects section boundaries, normalizes headings to canonical types,
    handles aliases, captures custom/unknown sections, and preserves original text.
    """

    # Canonical section mapping: canonical_type -> list of aliases (all lower-cased)
    SECTION_TAXONOMY: Dict[str, List[str]] = {
        "contact": [
            "contact",
            "contact information",
            "contact info",
            "contact details",
            "personal details",
            "personal information",
            "personal info",
            "reach me at",
        ],
        "summary": [
            "summary",
            "professional summary",
            "executive summary",
            "summary of qualifications",
            "profile",
            "professional profile",
            "career profile",
            "personal profile",
            "about me",
            "objective",
            "career objective",
            "professional objective",
            "overview",
            "biography",
        ],
        "skills": [
            "skills",
            "technical skills",
            "core skills",
            "key skills",
            "core competencies",
            "competencies",
            "skills & competencies",
            "skills and competencies",
            "skills & tools",
            "skills and tools",
            "technical competencies",
            "technologies",
            "tech stack",
            "technology stack",
            "programming languages",
            "tools & frameworks",
            "tools and frameworks",
            "areas of expertise",
            "technical proficiencies",
            "hard skills",
            "it skills",
        ],
        "experience": [
            "experience",
            "work experience",
            "professional experience",
            "employment",
            "employment history",
            "work history",
            "career history",
            "relevant experience",
            "professional background",
            "work background",
            "career experience",
            "internship experience",
            "internships",
        ],
        "education": [
            "education",
            "academic background",
            "academic history",
            "educational background",
            "educational qualifications",
            "academic qualifications",
            "qualifications",
            "degrees",
            "education & training",
            "education and training",
            "formal education",
        ],
        "projects": [
            "projects",
            "personal projects",
            "key projects",
            "academic projects",
            "technical projects",
            "selected projects",
            "project experience",
            "portfolio",
            "software projects",
            "featured projects",
        ],
        "certifications": [
            "certifications",
            "licenses",
            "certifications & licenses",
            "certifications and licenses",
            "professional certifications",
            "credentials",
            "certificates",
            "professional credentials",
            "accreditations",
        ],
        "achievements": [
            "achievements",
            "awards",
            "honors",
            "honors & awards",
            "honors and awards",
            "key accomplishments",
            "accomplishments",
            "recognitions",
            "awards & achievements",
        ],
        "languages": [
            "languages",
            "language proficiency",
            "language skills",
            "spoken languages",
        ],
        "interests": [
            "interests",
            "hobbies",
            "hobbies & interests",
            "hobbies and interests",
            "activities",
            "extracurricular activities",
            "volunteer experience",
            "volunteer work",
            "volunteering",
            "community involvement",
        ],
        "publications": [
            "publications",
            "research",
            "research papers",
            "whitepapers",
            "patents",
            "presentations",
        ],
    }

    def __init__(self):
        # Build inverted lookup for O(1) canonical mapping
        self._alias_to_canonical: Dict[str, str] = {}
        for canonical, aliases in self.SECTION_TAXONOMY.items():
            for alias in aliases:
                self._alias_to_canonical[alias] = canonical

    def _normalize_heading_text(self, text: str) -> str:
        """Strip punctuation, leading symbols, and lowercase for matching."""
        # Remove markdown heading hashes (#, ##, etc.)
        cleaned = re.sub(r"^#{1,6}\s*", "", text.strip())
        # Remove trailing colon, dash, or period
        cleaned = re.sub(r"[\:\-\.\=]+$", "", cleaned).strip()
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).lower()
        return cleaned

    def identify_heading(self, line: str, next_line: Optional[str] = None) -> Optional[Tuple[str, str, float]]:
        """
        Determine whether a line is a section heading.
        Returns (canonical_type, clean_heading, confidence) or None.
        """
        stripped = line.strip()
        if not stripped:
            return None

        # Exclude bullet lines or lines starting with numbers/symbols
        if re.match(r"^(\-|\*|\•|\d+[\.\)]|[a-zA-Z]\))\s+", stripped):
            return None

        # Exclude lines that are too long to be a heading (standard section headers are rarely > 50 chars)
        if len(stripped) > 55:
            return None

        # Exclude lines that end with period (sentences) unless it's a single word with period
        if stripped.endswith(".") and len(stripped.split()) > 2:
            return None

        normalized = self._normalize_heading_text(stripped)

        # 1. Direct alias match
        if normalized in self._alias_to_canonical:
            canonical = self._alias_to_canonical[normalized]
            return canonical, stripped, 1.0

        # 2. Check if next line is underline (e.g., '---' or '===')
        is_underlined = False
        if next_line is not None:
            nl = next_line.strip()
            if len(nl) >= 3 and all(c in "-=_~" for c in nl):
                is_underlined = True

        # 3. Check for Markdown heading e.g., '## Experience' or '# Skills'
        is_markdown = stripped.startswith("#") and len(stripped.split("#")[-1].strip()) > 0

        # 4. Check for ALL CAPS short heading
        is_all_caps = (
            stripped.isupper()
            and len(stripped) >= 3
            and not any(char.isdigit() for char in stripped)
            and len(stripped.split()) <= 5
        )

        # 5. Check if heading has a colon at the end e.g., 'TECHNICAL BACKGROUND:'
        has_trailing_colon = stripped.endswith(":") and len(stripped.split()) <= 5

        if is_underlined or is_markdown or is_all_caps or has_trailing_colon:
            # Check if partial alias matches inside the heading
            for alias, canonical in self._alias_to_canonical.items():
                if alias == normalized or normalized.startswith(alias) or normalized.endswith(alias):
                    return canonical, stripped, 0.9

            # If it has strong heading characteristics but unknown name -> custom section
            if is_all_caps or is_underlined or is_markdown:
                return "custom", stripped, 0.75

        return None

    def detect_sections(self, text: str) -> List[DetectedSection]:
        """
        Parse normalized resume text into structured sections.
        Returns an ordered list of DetectedSection items.
        """
        if not text or not text.strip():
            return []

        raw_lines = text.split("\n")
        lines = [line.strip() for line in raw_lines]

        # Scan for headings and their line indices
        heading_indices: List[Tuple[int, str, str, float]] = []  # (line_idx, canonical_type, raw_heading, conf)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else None
            match = self.identify_heading(line, next_line)
            if match:
                canonical, heading_text, conf = match
                heading_indices.append((i, canonical, heading_text, conf))
                # If underline decoration was present, skip the underline line
                if next_line and len(next_line.strip()) >= 3 and all(c in "-=_~" for c in next_line.strip()):
                    i += 1
            i += 1

        sections: List[DetectedSection] = []
        section_order = 0

        # Handle header/contact info if text exists before the first heading
        if heading_indices:
            first_idx = heading_indices[0][0]
            if first_idx > 0:
                header_content = "\n".join(raw_lines[0:first_idx]).strip()
                if header_content:
                    sections.append(
                        DetectedSection(
                            section_type="contact",
                            raw_heading="Contact Information",
                            content=header_content,
                            section_order=section_order,
                            confidence=0.85,
                        )
                    )
                    section_order += 1

        # Extract content between consecutive headings
        for idx, (line_idx, canonical, raw_heading, conf) in enumerate(heading_indices):
            start_line = line_idx + 1
            # If the next line was an underline, advance start_line by 1
            if start_line < len(raw_lines):
                test_line = raw_lines[start_line].strip()
                if len(test_line) >= 3 and all(c in "-=_~" for c in test_line):
                    start_line += 1

            if idx + 1 < len(heading_indices):
                end_line = heading_indices[idx + 1][0]
            else:
                end_line = len(raw_lines)

            content_lines = raw_lines[start_line:end_line]
            content = "\n".join(content_lines).strip()

            sections.append(
                DetectedSection(
                    section_type=canonical,
                    raw_heading=raw_heading,
                    content=content,
                    section_order=section_order,
                    confidence=conf,
                )
            )
            section_order += 1

        # If no headings were detected at all, treat entire text as unsegmented custom section
        if not sections:
            sections.append(
                DetectedSection(
                    section_type="summary",
                    raw_heading="Content",
                    content=text.strip(),
                    section_order=0,
                    confidence=0.5,
                )
            )

        return sections

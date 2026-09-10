# AI Resume Analyzer & Job Opportunity Matcher: System Architecture

## 1. System Overview

The **AI Resume Analyzer & Job Opportunity Matcher** is a multi-service platform providing intelligent, explainable career analytics. It allows candidates to upload resumes (PDF, DOCX, TXT), extracts structured entities and skills against a curated taxonomy, calculates deterministic resume and ATS compliance scores, analyzes job descriptions, calculates multi-signal match scores, identifies prioritized skill gaps, and generates targeted learning roadmaps and interview questions.

```
Candidate / User
       │
       ▼
┌──────────────────────────┐
│  React 18 + Vite + TS    │  Port 3000 / SPA
│  Tailwind CSS UI         │
└──────────────┬───────────┘
               │ JSON / Bearer JWT
               ▼
┌──────────────────────────┐
│  FastAPI 0.111 REST API  │  Port 8000
│  - Auth & Profile        │
│  - Resumes & Versions    │
│  - Section Detection     │
│  - Skills & Entities     │
│  - Scoring & ATS Engine  │
│  - Jobs & Requirements   │
│  - Matching & Gap Engine │
│  - AI Feedback & Roadmap │
└──────┬───────────┬───────┘
       │           │
       ▼           ▼
┌───────────┐ ┌───────────────┐
│PostgreSQL │ │ Redis 7.0     │
│16-Alpine  │ │ Broker & Cache│
└───────────┘ └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ Celery Worker │
              │ Async Tasks   │
              └───────────────┘
```

---

## 2. End-to-End Pipeline

### A. Resume Ingestion & Normalization
1. **Validation**: MIME type magic numbers (`application/pdf`, `docx`, `text/plain`), file size limit (10MB), extension whitelist, path traversal sanitization.
2. **Storage**: Safe cryptographic filename generation, local disk or cloud volume (`uploads/`).
3. **Extraction**:
   - PDF: PyMuPDF (`fitz`) page-by-page text stream with layout reconstruction.
   - DOCX: `python-docx` paragraph & table cell extraction.
   - TXT: UTF-8 / Latin-1 decoded text stream.
4. **Text Cleaning & Normalization**: Unicode normalization (NFKC), bullet point standardization (`•`, `-`, `*`), whitespace consolidation.

### B. Section Detection & Entity Extraction
1. **Section Detection**: Heuristic regex classification matching standard and custom variations for:
   - Summary / Objective
   - Experience / Work History
   - Education
   - Skills
   - Projects
   - Certifications
2. **Skill Taxonomy Matching**: Greedy phrase-matching against `data/skills_taxonomy.json` supporting exact matching, alias expansion (e.g. `k8s` → `Kubernetes`, `postgres` → `PostgreSQL`), multi-word tokens, and years of experience / proficiency heuristic extraction.
3. **Entity Extraction**:
   - Contact Info: Email, phone number, LinkedIn, GitHub, portfolio URLs, location.
   - Work Experience: Job titles, company names, start/end dates, bullet points.
   - Education: Degree type (Bachelors, Masters, PhD, etc.), institution, graduation year, GPA.
   - Projects & Certifications: Project name, technologies used, credential names.

### C. Deterministic Scoring & ATS Analysis
All numerical scores are 100% deterministic, explainable, and reproducible:
- **Skill Score (25%)**: Skill breadth, category diversity across languages, frameworks, cloud, databases, and DevOps.
- **Experience Score (25%)**: Role progression, duration, action verb density, quantified impact metrics.
- **ATS Compliance Score (20%)**: Section completeness, contact clarity, bullet length hygiene, avoidance of parsing hazards.
- **Project Score (10%)**: Number of structured projects and mapped technologies.
- **Education Score (10%)**: Degree clarity, accredited institution detection.
- **Structure Score (10%)**: Heading standardization, readability index, bullet point formatting.

### D. Job Description Parsing & Matching Engine
1. **Job Analysis**: Automatic requirement parsing into structured models:
   - Required skills (must-have)
   - Preferred skills (nice-to-have)
   - Minimum years of experience
   - Degree requirements
2. **Multi-Signal Matching**:
   - **Skill Match (40%)**: Jaccard & weighted overlap between resume skills and job requirements (`MATCHED`, `PARTIAL`, `MISSING`).
   - **Keyword & TF-IDF Match (25%)**: Normalized n-gram frequency comparison between resume and job description.
   - **Semantic Similarity (20%)**: Dense vector embeddings computed using `sentence-transformers` (`all-MiniLM-L6-v2`) and cosine similarity.
   - **Experience Match (10%)**: Resume candidate years vs. job requirement.
   - **Education Match (5%)**: Degree hierarchy comparison.

### E. AI Provider Abstraction
- Pluggable provider pattern: `BaseAIProvider` interface.
- `DeterministicMockAIProvider`: Works offline with zero API keys or external costs. Generates structured, truth-preserving recommendations, STAR-method bullet enhancements, personalized stage-by-stage learning curricula, and categorized interview prep.
- `OpenAIProvider`: Connects to OpenAI (`gpt-4o-mini` / `gpt-4o`) when `OPENAI_API_KEY` is provided.

---

## 3. Database Schema (19 SQLAlchemy Models)

| Model | Table | Description |
| :--- | :--- | :--- |
| `User` | `users` | Core user account, hashed credentials, role |
| `UserProfile` | `user_profiles` | Personal details, headline, target titles, URLs |
| `Resume` | `resumes` | Resume container, primary status, active version reference |
| `ResumeVersion` | `resume_versions` | Immutable version snapshot, extracted raw & clean text |
| `ResumeSection` | `resume_sections` | Section text chunks, classified section types |
| `ResumeSkill` | `resume_skills` | Extracted skills, category, proficiency, years |
| `Experience` | `experiences` | Work experience records, company, title, bullets |
| `Education` | `educations` | Degree, institution, field of study, graduation date |
| `Project` | `projects` | Project records, descriptions, URLs, technologies |
| `Certification` | `certifications` | License & certification names, issuers, dates |
| `ResumeScore` | `resume_scores` | Breakdown of deterministic scores, strengths, weaknesses |
| `JobDescription` | `job_descriptions` | Target job postings, title, company, full description |
| `JobRequirement` | `job_requirements` | Extracted structured job requirements & skills |
| `MatchResult` | `match_results` | Overall match score, component scores, matched/missing skills |
| `SkillGap` | `skill_gaps` | Prioritized missing skills (HIGH, MEDIUM, LOW), reasons |
| `AIFeedback` | `ai_feedbacks` | AI-generated summary, strengths, recommendations |
| `LearningRoadmap` | `learning_roadmaps` | Learning roadmap container for target job |
| `LearningRoadmapItem` | `learning_roadmap_items`| Structured learning stage, skill, priority, resources |
| `InterviewQuestion` | `interview_questions` | Category, difficulty, question, answer guidance |

---

## 4. Security & Compliance

- **Authentication**: JWT access tokens (HS256) + cryptographically secure refresh token rotation.
- **Passwords**: Passlib `bcrypt` hashing with salt rounds.
- **Data Isolation**: All queries enforce tenant isolation via `current_user.id`. Cross-user access returns HTTP 403 Forbidden.
- **Input Sanitization**: File uploads checked for extension, MIME header, and magic bytes. File names are stripped of path separators (`..`, `/`, `\`).
- **Untrusted Text Handling**: Resume and job description text are sanitized before NLP processing; prompt templates escape candidate text to prevent LLM prompt injection.

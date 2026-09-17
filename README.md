# AI-Powered Resume Analyzer & Job Opportunity Matcher

A production-ready platform that ingests resumes (PDF, DOCX, TXT), extracts structured entities and skills, computes explainable ATS and resume quality scores, compares resumes against job descriptions using multi-signal matching (exact, keyword TF-IDF, dense semantic embeddings), and generates personalized learning roadmaps and interview preparation guides.

---

## 🌟 Key Features

* **Secure Authentication**: OAuth2 password flow, JWT access & refresh tokens, bcrypt password hashing, and user-level tenant isolation.
* **Multi-Format Resume Ingestion**: Validates magic MIME bytes, file sizes, and parses PDF (`PyMuPDF`), DOCX (`python-docx`), and TXT with layout-aware text extraction.
* **Intelligent Section Detection**: Robust pattern matching identifying standard and custom resume sections (Summary, Experience, Education, Skills, Projects, Certifications).
* **Skill & Entity Extraction**:
  * Taxonomy of 1,200+ skills with aliases, multi-word matching, proficiency, and experience estimates.
  * Contact information, work history, degree & university, projects, and certifications.
* **Deterministic Scoring Engine**:
  * 100% explainable, deterministic scoring for Overall Quality, ATS Compliance, Skills, Experience, Education, Projects, and Structure.
  * Action verb density, quantifiable metrics detection, and bullet formatting analysis.
* **Job Opportunity System**:
  * Job description CRUD and automatic requirement extraction (required skills, preferred skills, experience, education).
* **Multi-Signal Matching Engine**:
  * Weighted combination of Skill Overlap (40%), TF-IDF Keyword Match (25%), Dense Semantic Similarity (20%), Experience Alignment (10%), and Education Fit (5%).
* **Skill Gap Engine**:
  * Categorizes missing skills into HIGH, MEDIUM, and LOW priority based on job requirement criticality.
* **Pluggable AI System**:
  * Works out of the box with `DeterministicMockAIProvider` (zero API key needed).
  * Seamlessly switches to `OpenAIProvider` (`gpt-4o-mini` / `gpt-4o`) when `OPENAI_API_KEY` is configured.
* **Career Enhancement Tools**:
  * **Resume Bullet Improver**: Rewrites resume bullets using the STAR method without fabricating facts.
  * **Personalized Learning Roadmap**: Milestone-based stages to bridge identified skill gaps.
  * **Targeted Interview Prep**: Technical, behavioral, project-based, and job-specific interview questions with model answers.
* **Complete React Frontend**:
  * Built with React 18, Vite, TypeScript, and Tailwind CSS.
  * Complete pages for Dashboard, Resumes, Jobs, Analysis, Learning Roadmap, Interview Prep, Analysis History, and Profile.

---

## 🛠️ Quickstart

### Option 1: Docker Compose (Recommended)

Run the full stack with PostgreSQL, Redis, Celery Worker, FastAPI backend, and Vite/Nginx frontend:

```bash
docker compose up --build
```

Access the services:
* **Frontend**: [http://localhost:3000](http://localhost:3000)
* **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option 2: Local Development Setup

#### 1. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI dev server
uvicorn app.main:app --reload --port 8000
```

#### 2. Start Celery Worker (Optional for background processing)

```bash
cd backend
celery -A app.tasks.celery_tasks.celery_app worker --loglevel=info
```

#### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Testing

### Backend Unit & Integration Tests

```bash
pytest backend/tests -v
```

All 60 tests verify:
- Authentication & JWT Token management
- Database models & Alembic schema integrity
- File upload validation & path traversal security
- Resume text extraction & section detection
- Skill taxonomy matching & entity extraction
- Deterministic scoring engine calculations
- Job description requirement parsing
- Multi-signal matching & skill gap prioritization
- AI provider bullet improvements & roadmap generation

### Frontend Build

```bash
cd frontend
npm run build
```

---

## 🔒 Security & Privacy

* **Strict Ownership Enforcement**: Every user-owned resource (`resume_id`, `job_id`, `analysis_id`) is strictly authorized against `current_user.id`.
* **Path Traversal Protection**: Uploaded file paths are sanitized with `secure_filename` to prevent directory traversal.
* **Magic Byte Validation**: Uploaded documents are verified against true file signatures rather than spoofable client-side MIME types.
* **No Fact Fabrication**: AI prompts explicitly enforce truth preservation, prohibiting the generation of unverified employers, numbers, or technologies.

---

## 🤖 Local LLM-Powered AI Resume Assistant

The platform includes an **AI Resume Assistant** powered by open-source instruction-tuned models from Hugging Face / Ollama running 100% locally on your machine with zero external paid APIs.

### 1. Installation & Dependencies
Install local inference packages inside `backend/.venv`:
```bash
pip install torch transformers accelerate
```

### 2. Model Configuration
Configure the assistant in `backend/.env`:
```env
# Hugging Face / Local Model Name
HF_MODEL_NAME=qwen2.5:7b
# Device selection: 'auto', 'cuda', or 'cpu'
HF_DEVICE=auto
# Max tokens to generate
HF_MAX_NEW_TOKENS=512
# Sampling temperature (low for factual adherence)
HF_TEMPERATURE=0.2
HF_TOP_P=0.9
```

Supported options:
- **Local Ollama Models**: e.g., `qwen2.5:7b`, `llama3.1:latest`, `qwen2.5-coder:7b`, `mistral:latest`.
- **Hugging Face Hub Repositories**: e.g., `Qwen/Qwen2.5-1.5B-Instruct`, `Qwen/Qwen2.5-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`.

### 3. Model Download & Cache Management
- Models are loaded once into memory on application startup or first query, avoiding redundant re-loads per request.
- Hugging Face weights are cached locally in `~/.cache/huggingface/hub`.
- Ollama weights are read from local Ollama storage (`~/.ollama/models`).

### 4. GPU/CPU Acceleration & Hardware Requirements
- **CUDA GPU Support**: Auto-detects NVIDIA GPUs (e.g. RTX 3050 Laptop GPU / RTX 3060 / 40-series). Loads in `float16` for high throughput.
- **CPU Fallback**: Gracefully falls back to CPU using `float32` if CUDA is unavailable.
- **VRAM Guidelines**:
  - `Qwen/Qwen2.5-1.5B-Instruct`: ~2 GB VRAM / 4 GB RAM.
  - `qwen2.5:7b` (4-bit quantized / GGUF): ~4.5 GB VRAM / 8 GB RAM.

### 5. Resume Context Builder
The context builder pulls verified database records strictly belonging to the authenticated user:
- Candidate identity and professional summary
- Extracted & normalized skills grouped by category
- Verified work experience, achievements, and responsibilities
- Degrees, institutions, and fields of study
- Technical projects and certifications
- Deterministic ATS score and keyword gap analysis
- Target job requirements and match scores (when job selected)

### 6. Multi-Signal Intent Detection
User inquiries are routed to dedicated prompt strategies without treating questions as bullet points:
- `RESUME_QUESTION`: Questions regarding resume quality, sections, or overall advice (e.g. *"What should I improve in my resume?"*, *"What i improve in my resume"*).
- `BULLET_REWRITE`: Action-verb and STAR refactoring (e.g. *"Developed a Python API"*, *"Improve this bullet: ..."*).
- `ATS_QUESTION`: Explanations of deterministic ATS score and keyword density.
- `SKILL_QUESTION`: Extracted skills and identified gap analysis.
- `JOB_MATCH_QUESTION`: Explanation of deterministic match percentage against a job.
- `GENERAL_CHAT`: Natural conversational courtesies and capabilities overview.

### 7. Anti-Hallucination & Truth Grounding
- **Database/NLP is Truth**: Scores, skills, and match percentages are computed by deterministic Python engines and provided to the LLM as facts.
- **Zero Metric Fabrication**: If the candidate's input lacks numbers (percentages, users, revenue), the assistant refactors using qualitative impact or prompts the candidate for actual metrics, never inventing fake numbers.
- **Unknown Skills**: If an inquiry asks about an unlisted skill (e.g. *"Do I have Kubernetes experience?"*), the assistant explicitly states it does not appear on the resume.

### 8. Running the Assistant
1. Ensure the FastAPI backend is running:
   ```bash
   cd backend && uvicorn app.main:app --port 8000
   ```
2. Start the React frontend:
   ```bash
   cd frontend && npm run dev
   ```
3. Open `http://localhost:5173/analysis`, select an uploaded resume, and ask any question or refactor any bullet point.

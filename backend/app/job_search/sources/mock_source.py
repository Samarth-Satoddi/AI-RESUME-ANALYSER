from datetime import datetime, timedelta, timezone
from typing import List
import uuid

from app.core.logging import logger
from app.job_search.base import JobSource
from app.job_search.schemas import JobSearchQuery, RawJobListing


class MockJobSource(JobSource):
    """
    Deterministic, offline job source adapter designed for testing, CI/CD,
    and development environments without live external network dependencies.
    Produces high-fidelity tech listings with realistic descriptions and skill profiles.
    """
    source_name = "mock_source"

    SEED_COMPANIES = [
        ("CloudScale Systems", "Bangalore, India", "hybrid", "https://example.com/careers/cloudscale"),
        ("Apex FinTech Labs", "Remote", "remote", "https://example.com/careers/apex-fintech"),
        ("DataMatrix Solutions", "Hyderabad, India", "on-site", "https://example.com/careers/datamatrix"),
        ("NextGen AI Research", "San Francisco, CA", "remote", "https://example.com/careers/nextgen-ai"),
        ("Quantum Health Technologies", "Bangalore, India", "hybrid", "https://example.com/careers/quantum-health"),
        ("Distributed Logic Inc.", "Remote", "remote", "https://example.com/careers/distributed-logic"),
        ("Nova Mobility Tech", "Pune, India", "hybrid", "https://example.com/careers/nova-mobility"),
    ]

    JOB_TEMPLATES = [
        {
            "suffix": "Engineer",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
            "preferred": ["Kubernetes", "AWS", "CI/CD"],
            "desc": (
                "We are seeking an experienced {title} to build resilient, distributed backend services.\n\n"
                "Key Responsibilities:\n"
                "- Architect high-throughput REST and async APIs using FastAPI and Python.\n"
                "- Design optimized relational schemas and execute zero-downtime migrations in PostgreSQL.\n"
                "- Containerize services with Docker and manage deployment pipelines.\n\n"
                "Qualifications & Requirements:\n"
                "- Required: Strong proficiency in Python, FastAPI, and relational databases (PostgreSQL or MySQL).\n"
                "- Required: 2+ years of software development experience with clean coding practices.\n"
                "- Preferred: Hands-on experience with Kubernetes, AWS, Redis caching, and microservices.\n"
                "- Education: Bachelor's degree in Computer Science, Engineering, or equivalent practical experience."
            ),
        },
        {
            "suffix": "Developer",
            "skills": ["Python", "Django", "PostgreSQL", "Celery", "REST APIs"],
            "preferred": ["React", "TypeScript", "GraphQL"],
            "desc": (
                "Join our platform engineering team as a {title}.\n\n"
                "Responsibilities:\n"
                "- Build, scale, and maintain customer-facing web applications.\n"
                "- Develop background worker tasks using Celery and Redis message brokers.\n"
                "- Collaborate with frontend engineers to integrate clean REST APIs.\n\n"
                "Requirements:\n"
                "- Required: 1-3 years of Python and web framework experience (FastAPI or Django).\n"
                "- Required: Solid understanding of relational database design and SQL queries.\n"
                "- Preferred: Experience with React, TypeScript, Docker, and modern CI/CD pipelines.\n"
                "- Degree in Computer Science or related STEM field."
            ),
        },
        {
            "suffix": "Specialist",
            "skills": ["Python", "SQL", "Pandas", "Scikit-Learn", "FastAPI"],
            "preferred": ["PyTorch", "MLOps", "Airflow"],
            "desc": (
                "We are expanding our analytics engineering squad and hiring a {title}.\n\n"
                "What You'll Do:\n"
                "- Build automated data pipelines and feature extraction services in Python.\n"
                "- Serve machine learning models behind low-latency REST endpoints.\n"
                "- Benchmark and evaluate model drift and prediction performance.\n\n"
                "What We Need:\n"
                "- Required: Python, SQL, Pandas, NumPy, and Scikit-Learn.\n"
                "- Required: Experience building production Python services.\n"
                "- Preferred: Cloud deployment on AWS or GCP, Airflow scheduling, PyTorch."
            ),
        },
    ]

    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """Generate deterministic, highly relevant job listings matching search terms."""
        logger.info(f"MockJobSource generating results for role='{query.role}' location='{query.location}'")
        base_role = query.role.strip() or "Software Engineer"
        results: List[RawJobListing] = []

        now = datetime.now(timezone.utc)

        count = min(query.limit or 15, len(self.SEED_COMPANIES) * 2)

        for i in range(count):
            comp_idx = i % len(self.SEED_COMPANIES)
            tmpl_idx = i % len(self.JOB_TEMPLATES)

            company, default_loc, default_remote, base_url = self.SEED_COMPANIES[comp_idx]
            template = self.JOB_TEMPLATES[tmpl_idx]

            # Adjust title variations
            if i % 3 == 0:
                title = f"Senior {base_role}"
            elif i % 3 == 1:
                title = f"{base_role}"
            else:
                title = f"Lead {base_role}"

            loc = query.location if (query.location and i % 2 == 0) else default_loc
            remote_type = "remote" if (query.remote or default_remote == "remote") else default_remote

            description = template["desc"].format(title=title)

            # Realistic days ago offset
            posted_days_ago = (i * 2) % (query.posted_within_days or 14)
            posted_at = now - timedelta(days=posted_days_ago, hours=i * 3)

            job_id = f"mock-{comp_idx + 1}-{i + 100}"

            results.append(
                RawJobListing(
                    external_id=job_id,
                    source="mock_source",
                    title=title,
                    company=company,
                    location=loc,
                    remote_type=remote_type,
                    employment_type=query.employment_type or "full-time",
                    salary_min=float(70000 + (i * 10000)) if i % 2 == 0 else None,
                    salary_max=float(110000 + (i * 12000)) if i % 2 == 0 else None,
                    currency="USD",
                    description=description,
                    url=f"{base_url}/job/{job_id}",
                    posted_at=posted_at,
                    collected_at=now,
                )
            )

        logger.info(f"MockJobSource provided {len(results)} synthetic listings")
        return results

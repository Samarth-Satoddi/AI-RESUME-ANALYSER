import pytest
from app.services.entity_extractor import EntityExtractor


def test_contact_info_extraction():
    """Verify parsing contact metadata: email, phone, LinkedIn, GitHub, name."""
    extractor = EntityExtractor()
    sample_text = """John Doe
    john.doe@techcorp.com | (415) 555-2671 | San Francisco, CA
    https://linkedin.com/in/johndoe | https://github.com/johndoe
    """
    contact = extractor.extract_contact_info(sample_text)

    assert contact.name == "John Doe"
    assert contact.email == "john.doe@techcorp.com"
    assert contact.phone == "(415) 555-2671"
    assert "linkedin.com/in/johndoe" in (contact.linkedin_url or "")
    assert "github.com/johndoe" in (contact.github_url or "")
    assert "San Francisco" in (contact.location or "")


def test_work_experience_extraction():
    """Verify parsing work experience with title, company, dates, and bullets."""
    extractor = EntityExtractor()
    section = """Senior Backend Engineer | CloudScale Inc | Jan 2021 - Present
    - Architected distributed data pipelines with Python and Kafka.
    - Reduced database query latency by 45%.

    Software Engineer | DataHub Corp | Jun 2018 - Dec 2020
    - Developed microservices using FastAPI and PostgreSQL.
    """
    experiences = extractor.extract_experiences(section)

    assert len(experiences) >= 2
    assert "CloudScale" in experiences[0].company
    assert "Backend Engineer" in experiences[0].job_title
    assert experiences[0].is_current is True

    assert "DataHub" in experiences[1].company
    assert "Jun 2018" in (experiences[1].start_date or "")


def test_education_extraction():
    """Verify parsing education institutions, degrees, and GPA."""
    extractor = EntityExtractor()
    section = """University of California, Berkeley
    Bachelor of Science in Computer Science | 2015 - 2019
    GPA: 3.8 / 4.0
    """
    educations = extractor.extract_education(section)

    assert len(educations) >= 1
    assert "Berkeley" in educations[0].institution
    assert "Bachelor of Science" in educations[0].degree
    assert "3.8" in (educations[0].grade or "")


def test_projects_and_certifications_extraction():
    """Verify parsing projects and professional certifications."""
    extractor = EntityExtractor()
    proj_section = """AI Resume Analyzer
    - Developed an NLP-powered resume optimization tool using Python and Transformers.
    - https://github.com/johndoe/resume-analyzer
    """
    projects = extractor.extract_projects(proj_section)
    assert len(projects) >= 1
    assert "AI Resume Analyzer" in projects[0].name
    assert projects[0].github_url is not None

    cert_section = """- AWS Certified Solutions Architect - Associate - Amazon Web Services
    - Terraform Certified Associate - HashiCorp
    """
    certs = extractor.extract_certifications(cert_section)
    assert len(certs) >= 2
    assert "AWS Certified Solutions Architect" in certs[0].name

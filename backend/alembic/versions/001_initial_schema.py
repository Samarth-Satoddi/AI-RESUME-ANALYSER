"""Initial schema migration with all models

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-10 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. profiles
    op.create_table(
        'profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('github_url', sa.String(length=500), nullable=True),
        sa.Column('portfolio_url', sa.String(length=500), nullable=True),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('years_of_experience', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_profiles_user_id'), 'profiles', ['user_id'], unique=True)

    # 3. resumes
    op.create_table(
        'resumes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resumes_user_id'), 'resumes', ['user_id'], unique=False)

    # 4. resume_versions
    op.create_table(
        'resume_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('parser_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resume_id', 'version_number', name='uq_resume_version_number'),
    )
    op.create_index(op.f('ix_resume_versions_resume_id'), 'resume_versions', ['resume_id'], unique=False)

    # 5. resume_sections
    op.create_table(
        'resume_sections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_version_id', sa.UUID(), nullable=False),
        sa.Column('section_type', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('section_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['resume_version_id'], ['resume_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resume_sections_resume_version_id'), 'resume_sections', ['resume_version_id'], unique=False)

    # 6. resume_skills
    op.create_table(
        'resume_skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_version_id', sa.UUID(), nullable=False),
        sa.Column('skill_name', sa.String(length=150), nullable=False),
        sa.Column('normalized_skill_name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('proficiency', sa.String(length=50), nullable=True),
        sa.Column('years_used', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['resume_version_id'], ['resume_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resume_skills_resume_version_id'), 'resume_skills', ['resume_version_id'], unique=False)
    op.create_index(op.f('ix_resume_skills_normalized_skill_name'), 'resume_skills', ['normalized_skill_name'], unique=False)

    # 7. experiences
    op.create_table(
        'experiences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_version_id', sa.UUID(), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('start_date', sa.String(length=50), nullable=True),
        sa.Column('end_date', sa.String(length=50), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['resume_version_id'], ['resume_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_experiences_resume_version_id'), 'experiences', ['resume_version_id'], unique=False)

    # 8. educations
    op.create_table(
        'educations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_version_id', sa.UUID(), nullable=False),
        sa.Column('institution', sa.String(length=255), nullable=False),
        sa.Column('degree', sa.String(length=255), nullable=False),
        sa.Column('field_of_study', sa.String(length=255), nullable=True),
        sa.Column('start_date', sa.String(length=50), nullable=True),
        sa.Column('end_date', sa.String(length=50), nullable=True),
        sa.Column('grade', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['resume_version_id'], ['resume_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_educations_resume_version_id'), 'educations', ['resume_version_id'], unique=False)

    # 9. projects
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_version_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('technologies', sa.JSON(), nullable=True),
        sa.Column('project_url', sa.String(length=500), nullable=True),
        sa.Column('github_url', sa.String(length=500), nullable=True),
        sa.Column('start_date', sa.String(length=50), nullable=True),
        sa.Column('end_date', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['resume_version_id'], ['resume_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_projects_resume_version_id'), 'projects', ['resume_version_id'], unique=False)

    # 10. certifications
    op.create_table(
        'certifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_version_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('issuing_organization', sa.String(length=255), nullable=False),
        sa.Column('issue_date', sa.String(length=50), nullable=True),
        sa.Column('expiration_date', sa.String(length=50), nullable=True),
        sa.Column('credential_id', sa.String(length=255), nullable=True),
        sa.Column('credential_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['resume_version_id'], ['resume_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_certifications_resume_version_id'), 'certifications', ['resume_version_id'], unique=False)

    # 11. job_descriptions
    op.create_table(
        'job_descriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_descriptions_user_id'), 'job_descriptions', ['user_id'], unique=False)

    # 12. job_requirements
    op.create_table(
        'job_requirements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('job_description_id', sa.UUID(), nullable=False),
        sa.Column('requirement_type', sa.String(length=100), nullable=False),
        sa.Column('requirement_text', sa.Text(), nullable=False),
        sa.Column('normalized_skill_name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('years_required', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['job_description_id'], ['job_descriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_requirements_job_description_id'), 'job_requirements', ['job_description_id'], unique=False)
    op.create_index(op.f('ix_job_requirements_normalized_skill_name'), 'job_requirements', ['normalized_skill_name'], unique=False)

    # 13. analyses
    op.create_table(
        'analyses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('resume_version_id', sa.UUID(), nullable=False),
        sa.Column('job_description_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('resume_score', sa.Float(), nullable=True),
        sa.Column('ats_score', sa.Float(), nullable=True),
        sa.Column('skill_score', sa.Float(), nullable=True),
        sa.Column('semantic_score', sa.Float(), nullable=True),
        sa.Column('experience_score', sa.Float(), nullable=True),
        sa.Column('keyword_score', sa.Float(), nullable=True),
        sa.Column('education_score', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_description_id'], ['job_descriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_version_id'], ['resume_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_analyses_user_id'), 'analyses', ['user_id'], unique=False)
    op.create_index(op.f('ix_analyses_resume_version_id'), 'analyses', ['resume_version_id'], unique=False)
    op.create_index(op.f('ix_analyses_job_description_id'), 'analyses', ['job_description_id'], unique=False)

    # 14. skill_matches
    op.create_table(
        'skill_matches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('analysis_id', sa.UUID(), nullable=False),
        sa.Column('skill_name', sa.String(length=150), nullable=False),
        sa.Column('resume_skill', sa.String(length=150), nullable=True),
        sa.Column('job_skill', sa.String(length=150), nullable=True),
        sa.Column('match_type', sa.String(length=50), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('importance', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_skill_matches_analysis_id'), 'skill_matches', ['analysis_id'], unique=False)

    # 15. missing_skills
    op.create_table(
        'missing_skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('analysis_id', sa.UUID(), nullable=False),
        sa.Column('skill_name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_missing_skills_analysis_id'), 'missing_skills', ['analysis_id'], unique=False)

    # 16. recommendations
    op.create_table(
        'recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('analysis_id', sa.UUID(), nullable=False),
        sa.Column('recommendation_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='medium'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recommendations_analysis_id'), 'recommendations', ['analysis_id'], unique=False)

    # 17. learning_roadmaps
    op.create_table(
        'learning_roadmaps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('analysis_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('estimated_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_learning_roadmaps_analysis_id'), 'learning_roadmaps', ['analysis_id'], unique=True)

    # 18. learning_roadmap_items
    op.create_table(
        'learning_roadmap_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('learning_roadmap_id', sa.UUID(), nullable=False),
        sa.Column('skill_name', sa.String(length=150), nullable=False),
        sa.Column('topic', sa.String(length=255), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('estimated_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('prerequisites', sa.JSON(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['learning_roadmap_id'], ['learning_roadmaps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_learning_roadmap_items_learning_roadmap_id'), 'learning_roadmap_items', ['learning_roadmap_id'], unique=False)

    # 19. interview_questions
    op.create_table(
        'interview_questions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('analysis_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('why_it_matters', sa.Text(), nullable=True),
        sa.Column('answer_guidance', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interview_questions_analysis_id'), 'interview_questions', ['analysis_id'], unique=False)


def downgrade() -> None:
    op.drop_table('interview_questions')
    op.drop_table('learning_roadmap_items')
    op.drop_table('learning_roadmaps')
    op.drop_table('recommendations')
    op.drop_table('missing_skills')
    op.drop_table('skill_matches')
    op.drop_table('analyses')
    op.drop_table('job_requirements')
    op.drop_table('job_descriptions')
    op.drop_table('certifications')
    op.drop_table('projects')
    op.drop_table('educations')
    op.drop_table('experiences')
    op.drop_table('resume_skills')
    op.drop_table('resume_sections')
    op.drop_table('resume_versions')
    op.drop_table('resumes')
    op.drop_table('profiles')
    op.drop_table('users')

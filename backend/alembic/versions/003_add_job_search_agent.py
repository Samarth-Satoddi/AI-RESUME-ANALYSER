"""Add job_searches, job_listings, job_search_results, and saved_jobs tables

Revision ID: 003_add_job_search_agent
Revises: 002_add_refresh_tokens
Create Date: 2026-09-10 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.db.base import GUID

# revision identifiers, used by Alembic.
revision: str = '003_add_job_search_agent'
down_revision: Union[str, None] = '002_add_refresh_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. job_searches
    op.create_table(
        'job_searches',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('resume_id', GUID(), nullable=True),
        sa.Column('query_role', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('remote', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('experience_level', sa.String(length=100), nullable=True),
        sa.Column('employment_type', sa.String(length=100), nullable=True),
        sa.Column('salary_min', sa.Float(), nullable=True),
        sa.Column('salary_max', sa.Float(), nullable=True),
        sa.Column('skills_filter', sa.Text(), nullable=True),
        sa.Column('posted_within_days', sa.Integer(), nullable=True, server_default='14'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('jobs_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jobs_analyzed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jobs_matched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_searches_user_id'), 'job_searches', ['user_id'])
    op.create_index(op.f('ix_job_searches_status'), 'job_searches', ['status'])

    # 2. job_listings
    op.create_table(
        'job_listings',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('remote_type', sa.String(length=50), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=True),
        sa.Column('salary_min', sa.Float(), nullable=True),
        sa.Column('salary_max', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('dedup_hash', sa.String(length=64), nullable=True),
        sa.Column('job_description_id', GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_description_id'], ['job_descriptions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_listings_source'), 'job_listings', ['source'])
    op.create_index(op.f('ix_job_listings_title'), 'job_listings', ['title'])
    op.create_index(op.f('ix_job_listings_company'), 'job_listings', ['company'])
    op.create_index(op.f('ix_job_listings_dedup_hash'), 'job_listings', ['dedup_hash'])

    # 3. job_search_results
    op.create_table(
        'job_search_results',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('search_id', GUID(), nullable=False),
        sa.Column('job_listing_id', GUID(), nullable=False),
        sa.Column('analysis_id', GUID(), nullable=True),
        sa.Column('overall_match_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('skill_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('keyword_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('semantic_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('experience_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('education_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('rank_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('rank', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('ai_explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['search_id'], ['job_searches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_listing_id'], ['job_listings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_search_results_search_id'), 'job_search_results', ['search_id'])
    op.create_index(op.f('ix_job_search_results_job_listing_id'), 'job_search_results', ['job_listing_id'])

    # 4. saved_jobs
    op.create_table(
        'saved_jobs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('job_listing_id', GUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='saved'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_listing_id'], ['job_listings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'job_listing_id', name='uq_user_saved_job'),
    )
    op.create_index(op.f('ix_saved_jobs_user_id'), 'saved_jobs', ['user_id'])
    op.create_index(op.f('ix_saved_jobs_status'), 'saved_jobs', ['status'])


def downgrade() -> None:
    op.drop_table('saved_jobs')
    op.drop_table('job_search_results')
    op.drop_table('job_listings')
    op.drop_table('job_searches')

"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-12-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Task table
    op.create_table(
        'task',
        sa.Column('task_id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        
        sa.Column('planned_start_utc', sa.DateTime(), nullable=False),
        sa.Column('planned_end_utc', sa.DateTime(), nullable=False),
        sa.Column('planned_duration_minutes', sa.Integer(), nullable=False),
        
        sa.Column('executed_start_utc', sa.DateTime(), nullable=True),
        sa.Column('executed_end_utc', sa.DateTime(), nullable=True),
        sa.Column('executed_duration_minutes', sa.Integer(), nullable=True),
        
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_modified_at', sa.DateTime(), nullable=False),
        sa.Column('notion_page_id', sa.String(100), unique=True, nullable=True),
        
        sa.CheckConstraint(
            "state IN ('PLANNED', 'EXECUTING', 'EXECUTED', 'SKIPPED', 'DELETED')",
            name='check_state'
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'voice')",
            name='check_source'
        ),
        sa.CheckConstraint(
            'planned_duration_minutes > 0',
            name='check_planned_duration'
        ),
    )
    
    op.create_index('idx_task_state', 'task', ['state'])
    op.create_index('idx_task_start', 'task', ['planned_start_utc'])
    op.create_index('idx_task_category', 'task', ['category'])
    op.create_index('idx_task_created', 'task', ['created_at'])
    
    # StopwatchSession table
    op.create_table(
        'stopwatch_session',
        sa.Column('session_id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), nullable=False),
        sa.Column('start_time_utc', sa.DateTime(), nullable=False),
        sa.Column('end_time_utc', sa.DateTime(), nullable=True),
        sa.Column('auto_closed', sa.Boolean(), default=False),
        
        sa.ForeignKeyConstraint(['task_id'], ['task.task_id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_stopwatch_task', 'stopwatch_session', ['task_id'])
    
    # CategoryMapping table
    op.create_table(
        'category_mapping',
        sa.Column('keyword', sa.String(100), primary_key=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float(), default=0.9),
        sa.Column('last_used', sa.DateTime(), nullable=False),
    )
    
    op.create_index(
        'idx_category_confidence',
        'category_mapping',
        ['category', 'confidence']
    )


def downgrade() -> None:
    op.drop_table('category_mapping')
    op.drop_table('stopwatch_session')
    op.drop_table('task')

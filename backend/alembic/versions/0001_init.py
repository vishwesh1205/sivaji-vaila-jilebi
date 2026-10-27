"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-10-25 13:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0001_init'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bureaus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=180), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bureaus_code'), 'bureaus', ['code'], unique=True)

    op.create_table(
        'institutions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aicte_permanent_id', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('normalized_name', sa.String(length=300), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=80), nullable=False),
        sa.Column('university_affiliation', sa.String(length=250), nullable=True),
        sa.Column('approval_status', sa.String(length=80), nullable=False),
        sa.Column('programme_mix', sa.JSON(), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aicte_permanent_id'),
    )
    op.create_index(op.f('ix_institutions_aicte_permanent_id'), 'institutions', ['aicte_permanent_id'], unique=True)
    op.create_index(op.f('ix_institutions_name'), 'institutions', ['name'], unique=False)
    op.create_index(op.f('ix_institutions_normalized_name'), 'institutions', ['normalized_name'], unique=False)
    op.create_index(op.f('ix_institutions_city'), 'institutions', ['city'], unique=False)
    op.create_index(op.f('ix_institutions_state'), 'institutions', ['state'], unique=False)
    op.create_index(op.f('ix_institutions_region'), 'institutions', ['region'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_institutions_region'), table_name='institutions')
    op.drop_index(op.f('ix_institutions_state'), table_name='institutions')
    op.drop_index(op.f('ix_institutions_city'), table_name='institutions')
    op.drop_index(op.f('ix_institutions_normalized_name'), table_name='institutions')
    op.drop_index(op.f('ix_institutions_name'), table_name='institutions')
    op.drop_index(op.f('ix_institutions_aicte_permanent_id'), table_name='institutions')
    op.drop_table('institutions')
    op.drop_index(op.f('ix_bureaus_code'), table_name='bureaus')
    op.drop_table('bureaus')

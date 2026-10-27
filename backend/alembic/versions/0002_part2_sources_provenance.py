"""part 2 data sources, provenance, risk and outcome fields

Revision ID: 0002_part2
Revises: 0001_init
Create Date: 2026-10-25 15:45:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0002_part2'
down_revision: Union[str, None] = '0001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c['name'] for c in insp.get_columns(table)}


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())

    if 'raw_payloads' not in tables:
        op.create_table(
            'raw_payloads',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('source', sa.String(length=80), nullable=False),
            sa.Column('source_record_id', sa.String(length=150), nullable=True),
            sa.Column('payload_json', sa.JSON(), nullable=False),
            sa.Column('payload_sha256', sa.String(length=64), nullable=False),
            sa.Column('source_type', sa.String(length=30), nullable=False),
            sa.Column('fetched_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_raw_payloads_source'), 'raw_payloads', ['source'], unique=False)
        op.create_index(op.f('ix_raw_payloads_source_record_id'), 'raw_payloads', ['source_record_id'], unique=False)
        op.create_index(op.f('ix_raw_payloads_payload_sha256'), 'raw_payloads', ['payload_sha256'], unique=False)
        op.create_index(op.f('ix_raw_payloads_fetched_at'), 'raw_payloads', ['fetched_at'], unique=False)

    for table, columns in {
        'data_sources': [
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=80), nullable=False),
            sa.Column('kind', sa.String(length=50), nullable=False),
            sa.Column('mode', sa.String(length=30), nullable=False),
            sa.Column('base_url_masked', sa.String(length=300), nullable=True),
            sa.Column('interval_seconds', sa.Integer(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.Column('last_status', sa.String(length=30), nullable=False),
            sa.Column('last_success_at', sa.DateTime(), nullable=True),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('records_total', sa.Integer(), nullable=False),
            sa.Column('latency_ms_avg', sa.Float(), nullable=False),
            sa.Column('source_type', sa.String(length=30), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        ],
        'sync_runs': [
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('source', sa.String(length=80), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=30), nullable=False),
            sa.Column('fetched', sa.Integer(), nullable=False),
            sa.Column('created', sa.Integer(), nullable=False),
            sa.Column('duplicates_skipped', sa.Integer(), nullable=False),
            sa.Column('auto_linked', sa.Integer(), nullable=False),
            sa.Column('sent_to_review', sa.Integer(), nullable=False),
            sa.Column('unresolved', sa.Integer(), nullable=False),
            sa.Column('errors_json', sa.JSON(), nullable=False),
            sa.Column('latency_ms', sa.Float(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        ],
        'public_stats': [
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('source', sa.String(length=80), nullable=False),
            sa.Column('dataset_key', sa.String(length=100), nullable=False),
            sa.Column('period', sa.String(length=50), nullable=True),
            sa.Column('dimension', sa.String(length=100), nullable=True),
            sa.Column('metrics_json', sa.JSON(), nullable=False),
            sa.Column('fetched_at', sa.DateTime(), nullable=False),
            sa.Column('is_snapshot', sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        ],
    }.items():
        if table in tables:
            continue
        op.create_table(table, *columns)
        if table != 'data_sources':
            op.create_index(op.f(f'ix_{table}_source'), table, ['source'], unique=False)

    op.create_index(op.f('ix_data_sources_name'), 'data_sources', ['name'], unique=True)
    op.create_index(op.f('ix_data_sources_enabled'), 'data_sources', ['enabled'], unique=False)
    op.create_index(op.f('ix_sync_runs_started_at'), 'sync_runs', ['started_at'], unique=False)
    op.create_index(op.f('ix_sync_runs_status'), 'sync_runs', ['status'], unique=False)
    op.create_index(op.f('ix_public_stats_fetched_at'), 'public_stats', ['fetched_at'], unique=False)
    op.create_index(op.f('ix_public_stats_is_snapshot'), 'public_stats', ['is_snapshot'], unique=False)

    inst_cols = _columns('institutions')
    if inst_cols:
        with op.batch_alter_table('institutions') as batch:
            if 'is_synthetic' not in inst_cols:
                batch.add_column(sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.true()))
            if 'source_type' not in inst_cols:
                batch.add_column(sa.Column('source_type', sa.String(length=30), nullable=False, server_default='SIMULATOR'))
        op.create_index(op.f('ix_institutions_is_synthetic'), 'institutions', ['is_synthetic'], unique=False)
        op.create_index(op.f('ix_institutions_source_type'), 'institutions', ['source_type'], unique=False)

    case_cols = _columns('cases')
    if case_cols:
        additions = {
            'source_type': sa.Column('source_type', sa.String(length=30), nullable=False, server_default='MANUAL'),
            'source_name': sa.Column('source_name', sa.String(length=80), nullable=True),
            'source_record_id': sa.Column('source_record_id', sa.String(length=150), nullable=True),
            'raw_payload_id': sa.Column('raw_payload_id', sa.Integer(), sa.ForeignKey('raw_payloads.id'), nullable=True),
            'complainant_hash': sa.Column('complainant_hash', sa.String(length=64), nullable=True),
            'language': sa.Column('language', sa.String(length=20), nullable=False, server_default='en'),
            'narrative_original': sa.Column('narrative_original', sa.Text(), nullable=True),
            'narrative_translated': sa.Column('narrative_translated', sa.Text(), nullable=True),
            'outcome_tag': sa.Column('outcome_tag', sa.String(length=40), nullable=True),
        }
        with op.batch_alter_table('cases') as batch:
            for name, column in additions.items():
                if name not in case_cols:
                    batch.add_column(column)
        for name in ['source_type', 'source_name', 'source_record_id', 'raw_payload_id', 'complainant_hash', 'outcome_tag']:
            op.create_index(op.f(f'ix_cases_{name}'), 'cases', [name], unique=False)


def downgrade() -> None:
    for name in ['source_type', 'source_name', 'source_record_id', 'raw_payload_id', 'complainant_hash', 'outcome_tag']:
        op.drop_index(op.f(f'ix_cases_{name}'), table_name='cases')
    case_cols = _columns('cases')
    if case_cols:
        with op.batch_alter_table('cases') as batch:
            for name in ['outcome_tag', 'narrative_translated', 'narrative_original', 'language', 'complainant_hash', 'raw_payload_id', 'source_record_id', 'source_name', 'source_type']:
                if name in case_cols:
                    batch.drop_column(name)
    inst_cols = _columns('institutions')
    if inst_cols:
        op.drop_index(op.f('ix_institutions_source_type'), table_name='institutions')
        op.drop_index(op.f('ix_institutions_is_synthetic'), table_name='institutions')
        with op.batch_alter_table('institutions') as batch:
            for name in ['source_type', 'is_synthetic']:
                if name in inst_cols:
                    batch.drop_column(name)
    op.drop_index(op.f('ix_public_stats_is_snapshot'), table_name='public_stats')
    op.drop_index(op.f('ix_public_stats_fetched_at'), table_name='public_stats')
    op.drop_index(op.f('ix_public_stats_source'), table_name='public_stats')
    op.drop_table('public_stats')
    op.drop_index(op.f('ix_sync_runs_status'), table_name='sync_runs')
    op.drop_index(op.f('ix_sync_runs_started_at'), table_name='sync_runs')
    op.drop_index(op.f('ix_sync_runs_source'), table_name='sync_runs')
    op.drop_table('sync_runs')
    op.drop_index(op.f('ix_data_sources_enabled'), table_name='data_sources')
    op.drop_index(op.f('ix_data_sources_name'), table_name='data_sources')
    op.drop_table('data_sources')
    op.drop_index(op.f('ix_raw_payloads_fetched_at'), table_name='raw_payloads')
    op.drop_index(op.f('ix_raw_payloads_payload_sha256'), table_name='raw_payloads')
    op.drop_index(op.f('ix_raw_payloads_source_record_id'), table_name='raw_payloads')
    op.drop_index(op.f('ix_raw_payloads_source'), table_name='raw_payloads')
    op.drop_table('raw_payloads')

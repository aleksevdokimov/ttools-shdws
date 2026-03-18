"""create_server_map_updates

Revision ID: create_server_map_updates
Revises: add_map_update_fields
Create Date: 2026-03-01 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'create_server_map_updates'
down_revision: Union[str, None] = 'add_map_update_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create server_map_updates table for logging map update operations."""
    op.create_table(
        'server_map_updates',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('villages_processed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('players_processed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('alliances_processed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for common queries
    op.create_index('idx_map_updates_server', 'server_map_updates', ['server_id'])
    op.create_index('idx_map_updates_status', 'server_map_updates', ['status'])
    op.create_index('idx_map_updates_started', 'server_map_updates', ['started_at'])


def downgrade() -> None:
    """Drop server_map_updates table."""
    op.drop_index('idx_map_updates_started', table_name='server_map_updates')
    op.drop_index('idx_map_updates_status', table_name='server_map_updates')
    op.drop_index('idx_map_updates_server', table_name='server_map_updates')
    op.drop_table('server_map_updates')

"""add_map_update_fields

Revision ID: add_map_update_fields
Revises: add_last_update_info
Create Date: 2026-03-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_map_update_fields'
down_revision: Union[str, None] = 'add_last_update_info'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === servers table ===
    # Add timezone field
    op.add_column('servers', sa.Column('timezone', sa.String(50), server_default='UTC', nullable=False))
    # Add is_updating flag for concurrent update protection
    op.add_column('servers', sa.Column('is_updating', sa.Boolean(), server_default='0', nullable=False))
    # Add last_update_started_at
    op.add_column('servers', sa.Column('last_update_started_at', sa.DateTime(), nullable=True))
    # Add last_update_finished_at
    op.add_column('servers', sa.Column('last_update_finished_at', sa.DateTime(), nullable=True))
    
    # Add index for active servers
    op.create_index('idx_servers_active', 'servers', ['is_active'])
    
    # === alliances table ===
    # Add players_count aggregate
    op.add_column('alliances', sa.Column('players_count', sa.Integer(), server_default='0', nullable=False))
    # Add population aggregate
    op.add_column('alliances', sa.Column('population', sa.BigInteger(), server_default='0', nullable=False))
    # Add last_seen_at for tracking deletions
    op.add_column('alliances', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    
    # Add indexes for alliances
    op.create_index('idx_alliances_server', 'alliances', ['server_id'])
    op.create_index('idx_alliances_server_tag', 'alliances', ['server_id', 'tag'])
    
    # === players table ===
    # Add villages_count aggregate
    op.add_column('players', sa.Column('villages_count', sa.Integer(), server_default='0', nullable=False))
    # Add last_seen_at for tracking deletions
    op.add_column('players', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    
    # Add indexes for players
    op.create_index('idx_players_server', 'players', ['server_id'])
    op.create_index('idx_players_server_alliance', 'players', ['server_id', 'alliance_id'])
    op.create_index('idx_players_server_name', 'players', ['server_id', 'name'])
    
    # === villages table ===
    # Add last_seen_at for tracking deletions
    op.add_column('villages', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    
    # Add indexes for villages
    op.create_index('villages_server_x_y_idx', 'villages', ['server_id', 'x', 'y'])
    op.create_index('villages_server_player_idx', 'villages', ['server_id', 'player_id'])
    op.create_index('villages_server_village_id_idx', 'villages', ['server_id', 'village_id'])


def downgrade() -> None:
    # === villages table ===
    op.drop_index('villages_server_village_id_idx', table_name='villages')
    op.drop_index('villages_server_player_idx', table_name='villages')
    op.drop_index('villages_server_x_y_idx', table_name='villages')
    op.drop_column('villages', 'last_seen_at')
    
    # === players table ===
    op.drop_index('idx_players_server_name', table_name='players')
    op.drop_index('idx_players_server_alliance', table_name='players')
    op.drop_index('idx_players_server', table_name='players')
    op.drop_column('players', 'last_seen_at')
    op.drop_column('players', 'villages_count')
    
    # === alliances table ===
    op.drop_index('idx_alliances_server_tag', table_name='alliances')
    op.drop_index('idx_alliances_server', table_name='alliances')
    op.drop_column('alliances', 'last_seen_at')
    op.drop_column('alliances', 'population')
    op.drop_column('alliances', 'players_count')
    
    # === servers table ===
    op.drop_index('idx_servers_active', table_name='servers')
    op.drop_column('servers', 'last_update_finished_at')
    op.drop_column('servers', 'last_update_started_at')
    op.drop_column('servers', 'is_updating')
    op.drop_column('servers', 'timezone')

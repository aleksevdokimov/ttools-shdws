"""add_game_tables

Revision ID: add_game_tables
Revises: update_roles
Create Date: 2026-02-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_game_tables'
down_revision: Union[str, None] = 'update_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Расширение таблицы users ===
    # Добавляем новые поля
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True, server_default=''))
    op.add_column('users', sa.Column('info', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))
    
    # === Таблица user_settings ===
    op.create_table('user_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # === Таблица servers ===
    op.create_table('servers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('url', sa.String(255), nullable=False),
        sa.Column('info', sa.Text(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=False, server_default='{"server_time": "UTC+1", "speed": "x1", "server_type": "Classic"}'),
        sa.Column('update_time', sa.Time(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_servers_name', 'servers', ['name'])
    
    # === Таблица user_servers ===
    op.create_table('user_servers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'server_id', name='uq_user_server')
    )
    
    # === Таблица races ===
    op.create_table('races',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # === Таблица alliances ===
    op.create_table('alliances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('alliance_id', sa.Integer(), nullable=True),
        sa.Column('tag', sa.String(20), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # === Таблица players ===
    op.create_table('players',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('alliance_id', sa.Integer(), nullable=True),
        sa.Column('population', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('race_id', sa.Integer(), nullable=True),
        sa.Column('info', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.ForeignKeyConstraint(['alliance_id'], ['alliances.id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_players_name', 'players', ['name'])
    
    # === Таблица villages ===
    op.create_table('villages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('map_id', sa.Integer(), nullable=True),
        sa.Column('village_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('x', sa.Integer(), nullable=True),
        sa.Column('y', sa.Integer(), nullable=True),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('race_id', sa.Integer(), nullable=True),
        sa.Column('village_type', sa.String(50), nullable=True),
        sa.Column('info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # === Таблица api_keys ===
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('key_value', sa.String(64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_value')
    )
    op.create_index('idx_api_keys_key', 'api_keys', ['key_value'])
    
    # === Таблица attacks ===
    op.create_table('attacks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('attacker_player_id', sa.Integer(), nullable=True),
        sa.Column('target_village_id', sa.Integer(), nullable=True),
        sa.Column('defender_player_id', sa.Integer(), nullable=True),
        sa.Column('alliance_id', sa.Integer(), nullable=True),
        sa.Column('arrival_time', sa.TIMESTAMP(), nullable=False),
        sa.Column('attack_type', sa.String(50), nullable=True),
        sa.Column('wave_group', sa.Integer(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.ForeignKeyConstraint(['attacker_player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['target_village_id'], ['villages.id'], ),
        sa.ForeignKeyConstraint(['defender_player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['alliance_id'], ['alliances.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для attacks
    op.create_index('idx_attacks_target_village_arrival', 'attacks', ['target_village_id', 'arrival_time'])
    op.create_index('idx_attacks_alliance_arrival', 'attacks', ['alliance_id', 'arrival_time'])
    op.create_index('idx_attacks_defender_arrival', 'attacks', ['defender_player_id', 'arrival_time'])
    op.create_index('idx_attacks_server_arrival', 'attacks', ['server_id', 'arrival_time'])


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке
    op.drop_index('idx_attacks_server_arrival', table_name='attacks')
    op.drop_index('idx_attacks_defender_arrival', table_name='attacks')
    op.drop_index('idx_attacks_alliance_arrival', table_name='attacks')
    op.drop_index('idx_attacks_target_village_arrival', table_name='attacks')
    op.drop_table('attacks')
    
    op.drop_index('idx_api_keys_key', table_name='api_keys')
    op.drop_table('api_keys')
    
    op.drop_table('villages')
    
    op.drop_index('idx_players_name', table_name='players')
    op.drop_table('players')
    
    op.drop_table('alliances')
    
    op.drop_table('races')
    
    op.drop_table('user_servers')
    
    op.drop_index('idx_servers_name', table_name='servers')
    op.drop_table('servers')
    
    op.drop_table('user_settings')
    
    # Удаляем новые поля из users
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'info')
    op.drop_column('users', 'password_hash')

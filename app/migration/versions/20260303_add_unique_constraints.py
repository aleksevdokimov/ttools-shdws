"""add_unique_constraints

Revision ID: add_unique_constraints
Revises: add_missing_game_fields
Create Date: 2026-03-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_unique_constraints'
down_revision: Union[str, None] = 'add_missing_game_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет уникальные ограничения для игровых таблиц.
    
    SQLite не поддерживает ALTER для ограничений, поэтому используем batch mode.
    """
    
    # Используем batch mode для SQLite
    with op.batch_alter_table('alliances', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_alliances_server_alliance_id',
            ['server_id', 'alliance_id']
        )
    
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_players_server_account_id',
            ['server_id', 'account_id']
        )
    
    with op.batch_alter_table('villages', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_villages_server_map_id',
            ['server_id', 'map_id']
        )


def downgrade() -> None:
    """Удаляет уникальные ограничения."""
    
    with op.batch_alter_table('villages', schema=None) as batch_op:
        batch_op.drop_constraint('uq_villages_server_map_id', type_='unique')
    
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_constraint('uq_players_server_account_id', type_='unique')
    
    with op.batch_alter_table('alliances', schema=None) as batch_op:
        batch_op.drop_constraint('uq_alliances_server_alliance_id', type_='unique')

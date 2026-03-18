"""add_missing_game_fields

Revision ID: add_missing_game_fields
Revises: seed_races
Create Date: 2026-03-01 14:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_missing_game_fields'
down_revision: Union[str, None] = 'seed_races'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет недостающее поле population в таблицу villages."""
    
    # === Таблица villages ===
    # Добавляем population (единственное недостающее поле)
    op.add_column('villages', sa.Column('population', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Удаляет добавленное поле."""
    
    # Таблица villages
    op.drop_column('villages', 'population')

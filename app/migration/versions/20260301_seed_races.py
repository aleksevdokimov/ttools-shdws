"""seed_races

Revision ID: seed_races
Revises: create_server_map_updates
Create Date: 2026-03-01 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'seed_races'
down_revision: Union[str, None] = 'create_server_map_updates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed the races table with Travian races."""
    # Используем execute вместо bulk_insert для SQLite
    op.execute("""
        INSERT INTO races (id, name) VALUES 
        (1, 'Romans'),
        (2, 'Teutons'),
        (3, 'Gauls'),
        (4, 'Nature'),
        (5, 'Natars'),
        (6, 'Egyptians'),
        (7, 'Huns'),
        (8, 'Spartans')
    """)


def downgrade() -> None:
    """Remove seeded races."""
    op.execute("DELETE FROM races WHERE id IN (1, 2, 3, 4, 5, 6, 7, 8)")

"""add_oasis_50_percent_type_fields

Revision ID: 5707ba28e98b
Revises: e252725c11d1
Create Date: 2026-03-13 11:16:01.856119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5707ba28e98b'
down_revision: Union[str, None] = 'e252725c11d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO type_fields (name, wood_fields, clay_fields, iron_fields, crop_fields, wood_bonus, clay_bonus, iron_bonus, crop_bonus, can_be_settled, can_be_attacked) VALUES
        ('Oasis iron 50%', NULL, NULL, NULL, NULL, NULL, NULL, 50, NULL, 0, 1),
        ('Oasis wood 50%', NULL, NULL, NULL, NULL, 50, NULL, NULL, NULL, 0, 1),
        ('Oasis clay 50%', NULL, NULL, NULL, NULL, NULL, 50, NULL, NULL, 0, 1)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM type_fields WHERE name IN ('Oasis iron 50%', 'Oasis wood 50%', 'Oasis clay 50%')")

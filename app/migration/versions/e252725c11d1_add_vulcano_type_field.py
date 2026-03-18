"""add_vulcano_type_field

Revision ID: e252725c11d1
Revises: add_type_fields_and_maps
Create Date: 2026-03-13 09:29:28.219025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e252725c11d1'
down_revision: Union[str, None] = 'add_type_fields_and_maps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO type_fields (name, wood_fields, clay_fields, iron_fields, crop_fields, wood_bonus, clay_bonus, iron_bonus, crop_bonus, can_be_settled, can_be_attacked) VALUES
        ('Vulcano', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 0)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM type_fields WHERE name = 'Vulcano'")

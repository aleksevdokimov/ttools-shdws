"""merge heads

Revision ID: f23d696efa07
Revises: add_map_features, 5707ba28e98b
Create Date: 2026-03-18 13:05:55.572302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f23d696efa07'
down_revision: Union[str, None] = ('add_map_features', '5707ba28e98b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

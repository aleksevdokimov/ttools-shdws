"""remove_password_field

Revision ID: 2fe09b612ed6
Revises: 7a3d057662c9
Create Date: 2026-03-18 14:34:47.305725

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fe09b612ed6'
down_revision: Union[str, None] = '7a3d057662c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('users', 'password')


def downgrade() -> None:
    op.add_column('users', sa.Column('password', sa.String(), nullable=False))

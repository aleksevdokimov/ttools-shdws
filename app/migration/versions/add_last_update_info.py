"""add_last_update_info_to_servers

Revision ID: add_last_update_info
Revises: 
Create Date: 2026-02-28 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_last_update_info'
down_revision: Union[str, None] = 'add_user_id_index_to_user_servers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('servers', sa.Column('last_update_info', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('servers', 'last_update_info')

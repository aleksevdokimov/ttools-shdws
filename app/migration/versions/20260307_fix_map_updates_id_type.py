"""fix_map_updates_id_type

Revision ID: fix_map_updates_id_type
Revises: add_unique_constraints
Create Date: 2026-03-07 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_map_updates_id_type'
down_revision: Union[str, None] = 'af396e7edc7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change server_map_updates.id from BigInteger to Integer for SQLite compatibility.
    SQLite requires INTEGER PRIMARY KEY for autoincrement to work properly.
    """
    # SQLite doesn't support ALTER COLUMN TYPE directly, use batch_alter_table
    with op.batch_alter_table('server_map_updates', schema=None) as batch_op:
        batch_op.alter_column('id',
                           existing_type=sa.BigInteger(),
                           type_=sa.Integer(),
                           existing_nullable=False,
                           autoincrement=True)


def downgrade() -> None:
    """Revert back to BigInteger."""
    with op.batch_alter_table('server_map_updates', schema=None) as batch_op:
        batch_op.alter_column('id',
                           existing_type=sa.Integer(),
                           type_=sa.BigInteger(),
                           existing_nullable=False,
                           autoincrement=True)

"""empty message

Revision ID: af396e7edc7a
Revises: add_unique_constraints
Create Date: 2026-03-02 00:02:51.910582

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af396e7edc7a'
down_revision: Union[str, None] = 'add_unique_constraints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет недостающее поле population в таблицу villages."""
    
    # SQLite требует batch mode для добавления колонок
    with op.batch_alter_table('villages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('population', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Удаляет добавленное поле."""
    
    with op.batch_alter_table('villages', schema=None) as batch_op:
        batch_op.drop_column('population')


"""add registration_tokens table

Revision ID: 7a3d057662c9
Revises: f23d696efa07
Create Date: 2026-03-18 13:07:33.270431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a3d057662c9'
down_revision: Union[str, None] = 'f23d696efa07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('registrationtokens',
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('used_by_user_id', sa.Integer(), nullable=True),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('comment', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.ForeignKeyConstraint(['used_by_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token')
    )


def downgrade() -> None:
    op.drop_table('registrationtokens')

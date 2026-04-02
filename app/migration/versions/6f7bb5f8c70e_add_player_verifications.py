"""add_player_verifications

Revision ID: 6f7bb5f8c70e
Revises: 2fe09b612ed6
Create Date: 2026-03-31 16:45:47.117668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f7bb5f8c70e'
down_revision: Union[str, None] = '2fe09b612ed6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Только создаём новую таблицу player_verifications
    op.create_table('player_verifications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('player_id', sa.Integer(), nullable=False),
    sa.Column('server_id', sa.Integer(), nullable=False),
    sa.Column('verification_code', sa.String(length=10), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('verified_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
    sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'player_id', name='uq_user_player')
    )
    op.create_index('idx_player_verifications_player_id', 'player_verifications', ['player_id'], unique=False)
    op.create_index('idx_player_verifications_user_id', 'player_verifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_player_verifications_user_id', table_name='player_verifications')
    op.drop_index('idx_player_verifications_player_id', table_name='player_verifications')
    op.drop_table('player_verifications')

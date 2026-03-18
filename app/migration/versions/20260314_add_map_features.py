"""add_map_features

Revision ID: add_map_features
Revises: add_type_fields_and_maps
Create Date: 2026-03-14 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_map_features'
down_revision: Union[str, None] = 'add_type_fields_and_maps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица map_features
    op.create_table('map_features',
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('x', sa.Integer(), nullable=False),
        sa.Column('y', sa.Integer(), nullable=False),
        sa.Column('field_type', sa.Integer(), nullable=False),  # 6, 7, 9, 15
        sa.Column('oasis_wood', sa.Integer(), nullable=True),
        sa.Column('oasis_clay', sa.Integer(), nullable=True),
        sa.Column('oasis_iron', sa.Integer(), nullable=True),
        sa.Column('oasis_crop', sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id']),
        sa.PrimaryKeyConstraint('server_id', 'x', 'y')
    )

    # Индекс на field_type
    op.create_index('idx_map_features_field_type', 'map_features', ['field_type'])


def downgrade() -> None:
    op.drop_index('idx_map_features_field_type', table_name='map_features')
    op.drop_table('map_features')
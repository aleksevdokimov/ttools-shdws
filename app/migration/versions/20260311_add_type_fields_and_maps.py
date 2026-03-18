"""add_type_fields_and_maps

Revision ID: add_type_fields_and_maps
Revises: fix_map_updates_id_type
Create Date: 2026-03-11 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_type_fields_and_maps'
down_revision: Union[str, None] = 'fix_map_updates_id_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица type_fields
    op.create_table('type_fields',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('wood_fields', sa.Integer(), nullable=True),
        sa.Column('clay_fields', sa.Integer(), nullable=True),
        sa.Column('iron_fields', sa.Integer(), nullable=True),
        sa.Column('crop_fields', sa.Integer(), nullable=True),
        sa.Column('wood_bonus', sa.Integer(), nullable=True),
        sa.Column('clay_bonus', sa.Integer(), nullable=True),
        sa.Column('iron_bonus', sa.Integer(), nullable=True),
        sa.Column('crop_bonus', sa.Integer(), nullable=True),
        sa.Column('can_be_settled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('can_be_attacked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Заполнение справочника type_fields (используем execute вместо bulk_insert)
    op.execute("""
        INSERT INTO type_fields (name, wood_fields, clay_fields, iron_fields, crop_fields, wood_bonus, clay_bonus, iron_bonus, crop_bonus, can_be_settled, can_be_attacked) VALUES
        ('Oasis wood 25%', NULL, NULL, NULL, NULL, 25, NULL, NULL, NULL, 0, 1),
        ('Oasis wood 25% crop 25%', NULL, NULL, NULL, NULL, 25, NULL, NULL, 25, 0, 1),
        ('Oasis clay 25%', NULL, NULL, NULL, NULL, NULL, 25, NULL, NULL, 0, 1),
        ('Oasis clay 25% crop 25%', NULL, NULL, NULL, NULL, NULL, 25, NULL, 25, 0, 1),
        ('Oasis iron 25%', NULL, NULL, NULL, NULL, NULL, NULL, 25, NULL, 0, 1),
        ('Oasis iron 25% crop 25%', NULL, NULL, NULL, NULL, NULL, NULL, 25, 25, 0, 1),
        ('Oasis crop 25%', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 25, 0, 1),
        ('Oasis crop 50%', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 50, 0, 1),
        ('Field 3-3-3-9', 3, 3, 3, 9, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 3-4-5-6', 3, 4, 5, 6, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 4-4-4-6', 4, 4, 4, 6, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 4-5-3-6', 4, 5, 3, 6, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 5-3-4-6', 5, 3, 4, 6, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 1-1-1-15', 1, 1, 1, 15, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 4-4-3-7', 4, 4, 3, 7, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 3-4-4-7', 3, 4, 4, 7, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 4-3-4-7', 4, 3, 4, 7, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 3-5-4-6', 3, 5, 4, 6, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 4-3-5-6', 4, 3, 5, 6, NULL, NULL, NULL, NULL, 1, 0),
        ('Field 5-4-3-6', 5, 4, 3, 6, NULL, NULL, NULL, NULL, 1, 0),
        ('Forest', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 0),
        ('Lake', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 0),
        ('Mountain', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 0),
        ('Clay', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 0)
    """)
    
    # Таблица maps (с составным первичным ключом)
    op.create_table('maps',
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('x', sa.Integer(), nullable=False),
        sa.Column('y', sa.Integer(), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id']),
        sa.ForeignKeyConstraint(['type_id'], ['type_fields.id']),
        sa.PrimaryKeyConstraint('server_id', 'x', 'y')
    )
    
    # Индексы
    op.create_index('idx_maps_type', 'maps', ['type_id'])


def downgrade() -> None:
    op.drop_index('idx_maps_type', table_name='maps')
    op.drop_table('maps')
    op.execute('DELETE FROM type_fields')
    op.drop_table('type_fields')

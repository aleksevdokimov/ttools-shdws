"""Добавить updated_at в таблицу user_servers

Revision ID: 20260226_add_updated_at
Revises: 20260226_add_user_id
Create Date: 2026-02-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260226_add_updated_at'
down_revision = '20260226_add_user_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем, существует ли уже колонка
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(user_servers)"))
    columns = [row[1] for row in result]
    
    if 'updated_at' not in columns:
        with op.batch_alter_table('user_servers') as batch_op:
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
    else:
        print("Column 'updated_at' already exists, skipping...")


def downgrade() -> None:
    with op.batch_alter_table('user_servers') as batch_op:
        batch_op.drop_column('updated_at')

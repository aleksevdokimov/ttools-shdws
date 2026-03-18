"""Добавить user_id в таблицу players

Revision ID: 20260226_add_user_id
Revises: add_game_tables
Create Date: 2026-02-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260226_add_user_id'
down_revision = 'add_game_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем, существует ли уже колонка
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(players)"))
    columns = [row[1] for row in result]
    
    if 'user_id' not in columns:
        # Добавляем колонку без ограничения
        with op.batch_alter_table('players') as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        
        # Затем добавляем foreign key
        op.create_foreign_key('fk_players_user_id', 'players', 'users', ['user_id'], ['id'])
    else:
        print("Column 'user_id' already exists, skipping...")


def downgrade() -> None:
    # Проверяем, существует ли foreign key
    conn = op.get_bind()
    try:
        op.drop_constraint('fk_players_user_id', 'players', type_='foreignkey')
    except Exception:
        pass
    
    with op.batch_alter_table('players') as batch_op:
        batch_op.drop_column('user_id')

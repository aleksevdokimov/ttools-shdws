"""Add unique index on servers.url

Revision ID: add_unique_url_index
Revises: 20260226_add_user_id_to_players
Create Date: 2026-02-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_unique_url_index'
down_revision = '20260226_add_updated_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаём уникальный индекс на поле url
    # Проверяем, существует ли индекс уже
    connection = op.get_bind()
    
    # Для SQLite используем простое создание индекса
    # Индекс будет уникальным, но SQLite允许 NULL значений быть несколько раз
    op.create_index(
        'ix_servers_url_unique',
        'servers',
        ['url'],
        unique=True,
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index('ix_servers_url_unique', table_name='servers')

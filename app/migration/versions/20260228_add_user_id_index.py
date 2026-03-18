"""Добавить индекс для user_id в user_servers

Revision ID: add_user_id_index_to_user_servers
Revises: 20260227_migrate_passwords
Create Date: 2026-02-26

"""
from alembic import op

# revision identifiers
revision = 'add_user_id_index_to_user_servers'
down_revision = '20260227_migrate_passwords'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляем индекс для user_id."""
    op.create_index(
        'idx_user_servers_user_id',
        'user_servers',
        ['user_id'],
        unique=False
    )


def downgrade() -> None:
    """Удаляем индекс для user_id."""
    op.drop_index(
        'idx_user_servers_user_id',
        table_name='user_servers'
    )

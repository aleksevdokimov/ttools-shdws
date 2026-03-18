"""Copy password to password_hash for existing users

Revision ID: 20260227_migrate_passwords
Revises: 
Create Date: 2026-02-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260227_migrate_passwords'
down_revision = 'add_unique_url_index'  # Замените на последнюю миграцию
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Копируем пароли из старого поля password в password_hash
    # Только для записей, где password_hash пустой, а password нет
    op.execute("""
        UPDATE users 
        SET password_hash = password 
        WHERE password_hash = '' AND password != ''
    """)


def downgrade() -> None:
    # Обратная миграция не требуется - данные уже скопированы
    pass

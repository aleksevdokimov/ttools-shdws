"""update_roles

Revision ID: update_roles
Revises: e4d25cae4065
Create Date: 2026-02-24 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'update_roles'
down_revision: Union[str, None] = 'e4d25cae4065'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем всех пользователей (чистая установка)
    op.execute("DELETE FROM users")
    
    # Удаляем все существующие роли
    op.execute("DELETE FROM roles")
    
    # Вставляем новые роли с явными ID
    # id=1: Игрок (базовая роль)
    # id=2: Модератор
    # id=3: Альянс-модератор
    # id=4: Админ
    op.execute("INSERT INTO roles (id, name) VALUES (1, 'Игрок')")
    op.execute("INSERT INTO roles (id, name) VALUES (2, 'Модератор')")
    op.execute("INSERT INTO roles (id, name) VALUES (3, 'Альянс-модератор')")
    op.execute("INSERT INTO roles (id, name) VALUES (4, 'Админ')")
    
    # Обновляем role_id у всех существующих пользователей на 1 (Игрок)
    # Но т.к. мы удалили всех пользователей выше, это не нужно
    # Оставляем для совместимости с моделью SQLAlchemy
    op.execute("UPDATE users SET role_id = 1 WHERE role_id IS NULL OR role_id NOT IN (1, 2, 3, 4)")


def downgrade() -> None:
    # Удаляем новые роли
    op.execute("DELETE FROM users")
    op.execute("DELETE FROM roles")
    
    # Возвращаем старую роль
    op.execute("INSERT INTO roles (id, name) VALUES (1, 'user')")

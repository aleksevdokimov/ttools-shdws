# app/domain/permissions/entities.py
"""
Domain entities - чистый Python, без зависимостей от инфраструктуры.
"""

from enum import Enum
from typing import Set, Optional, List, Protocol
from dataclasses import dataclass


class Permission(str, Enum):
    """
    Все разрешения в системе.
    Это чистый domain объект, не зависит от БД.
    """
    
    # Серверы
    SERVERS_VIEW_ALL = "servers:view_all"
    SERVERS_MANAGE = "servers:manage"
    SERVERS_DELETE = "servers:delete"
    
    # Пользователи
    USERS_VIEW = "users:view"
    USERS_CREATE = "users:create"
    USERS_EDIT = "users:edit"
    USERS_DELETE = "users:delete"
    
    # Ключи
    KEYS_VIEW = "keys:view"
    KEYS_CREATE = "keys:create"
    KEYS_DELETE = "keys:delete"
    
    # Игровые данные
    GAME_VIEW = "game:view"
    GAME_EXPORT = "game:export"
    
    # Личные данные
    MY_SERVERS_VIEW = "my_servers:view"
    PROFILE_VIEW = "profile:view"
    PROFILE_EDIT = "profile:edit"
    
    # API
    API_KEYS_MANAGE = "api_keys:manage"
    
    # Аудит
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"


class Role(str, Enum):
    """
    Роли пользователей.
    Использует строковые значения, не привязан к БД.
    """
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass(frozen=True)
class UserContext:
    """
    Контекст пользователя для проверки прав.
    Содержит только domain данные, не зависит от ORM.
    """
    user_id: str  # Используем строку, чтобы не привязываться к типу БД
    role: Role
    is_active: bool = True
    
    @property
    def is_super_admin(self) -> bool:
        """Удобный хелпер для проверки суперадмина."""
        return self.role == Role.SUPER_ADMIN


# ============================================================================
# Domain Interfaces (для DIP)
# ============================================================================

class PermissionProvider(Protocol):
    """
    Интерфейс для получения разрешений.
    Domain определяет контракт, инфраструктура реализует.
    """
    
    def get_permissions(self, role: Role) -> Set[Permission]:
        """Получить все разрешения для роли."""
        ...
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Проверить наличие конкретного разрешения."""
        ...
    
    def get_roles_with_permission(self, permission: Permission) -> List[Role]:
        """Получить список ролей, имеющих разрешение."""
        ...

"""
Настройка DI контейнера для разрешений.
"""

from app.domain.permissions import PermissionService
from app.infrastructure.permissions.providers import StaticPermissionProvider
from app.infrastructure.permissions.mapper import UserContextMapper


# Создаем экземпляры (можно вынести в отдельный файл)
_permission_provider = StaticPermissionProvider()
_permission_service = PermissionService(_permission_provider)


def get_permission_service() -> PermissionService:
    """Dependency для получения сервиса разрешений."""
    return _permission_service


def get_user_context_mapper() -> UserContextMapper:
    """Dependency для получения маппера."""
    return UserContextMapper()
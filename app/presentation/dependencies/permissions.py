# app/presentation/dependencies/permissions.py
"""
FastAPI зависимости для работы с разрешениями.
Только presentation слой, никакой бизнес-логики.
"""

from typing import Optional, Set, List
from fastapi import Depends
from app.auth.models import User
from app.dependencies.auth_dep import get_current_user
from app.domain.permissions import Permission, UserContext, PermissionService
from app.infrastructure.permissions.setup import get_permission_service, get_user_context_mapper
from app.infrastructure.permissions.mapper import UserContextMapper
from app.exceptions import ForbiddenException


# ============================================================================
# Core Dependencies
# ============================================================================

async def get_user_context(
    user: Optional[User] = Depends(get_current_user),
    mapper: UserContextMapper = Depends(get_user_context_mapper),
) -> Optional[UserContext]:
    """
    Получить контекст пользователя.
    Преобразует ORM модель в domain объект.
    """
    if not user:
        return None
    
    return mapper.from_orm(user)


async def get_user_permissions(
    user_context: Optional[UserContext] = Depends(get_user_context),
    service: PermissionService = Depends(get_permission_service),
) -> Set[Permission]:
    """
    Получить все разрешения текущего пользователя.
    """
    return service.get_user_permissions(user_context)


# ============================================================================
# Permission Check Dependencies (только один источник)
# ============================================================================

def require_permission(permission: Permission):
    """
    Фабрика зависимостей для проверки конкретного разрешения.
    Возвращает UserContext, а не bool - это единственный источник.
    
    Usage:
        @router.get("/users")
        async def users_page(
            user_context: UserContext = Depends(require_permission(Permission.USERS_VIEW))
        ):
            ...
    """
    async def dependency(
        user_context: Optional[UserContext] = Depends(get_user_context),
        service: PermissionService = Depends(get_permission_service),
    ) -> UserContext:
        if not user_context:
            raise ForbiddenException("Требуется авторизация")
        
        if not service.has_permission(user_context, permission):
            raise ForbiddenException(f"Требуется разрешение: {permission.value}")
        
        return user_context
    
    return dependency


def require_any_permission(permissions: List[Permission]):
    """
    Фабрика зависимостей для проверки наличия любого разрешения.
    """
    async def dependency(
        user_context: Optional[UserContext] = Depends(get_user_context),
        service: PermissionService = Depends(get_permission_service),
    ) -> UserContext:
        if not user_context:
            raise ForbiddenException("Требуется авторизация")
        
        if not service.has_any_permission(user_context, permissions):
            perm_names = [p.value for p in permissions]
            raise ForbiddenException(f"Требуется одно из разрешений: {', '.join(perm_names)}")
        
        return user_context
    
    return dependency


def require_all_permissions(permissions: List[Permission]):
    """
    Фабрика зависимостей для проверки наличия всех разрешений.
    """
    async def dependency(
        user_context: Optional[UserContext] = Depends(get_user_context),
        service: PermissionService = Depends(get_permission_service),
    ) -> UserContext:
        if not user_context:
            raise ForbiddenException("Требуется авторизация")
        
        if not service.has_all_permissions(user_context, permissions):
            perm_names = [p.value for p in permissions]
            raise ForbiddenException(f"Требуются все разрешения: {', '.join(perm_names)}")
        
        return user_context
    
    return dependency


# ============================================================================
# UI Helpers
# ============================================================================

class UIPermissionMapper:
    """
    Маппер для преобразования domain permissions в UI флаги.
    Чисто presentation логика.
    """
    
    @staticmethod
    def to_ui_flags(permissions: Set[Permission]) -> dict:
        """
        Конвертирует набор разрешений в UI флаги.
        """
        return {
            # Навигация
            "nav_servers": Permission.SERVERS_VIEW_ALL in permissions,
            "nav_users": Permission.USERS_VIEW in permissions,
            "nav_my_servers": Permission.MY_SERVERS_VIEW in permissions,
            "nav_keys": Permission.KEYS_VIEW in permissions,
            "nav_audit": Permission.AUDIT_VIEW in permissions,
            
            # Действия
            "can_create_server": Permission.SERVERS_MANAGE in permissions,
            "can_edit_server": Permission.SERVERS_MANAGE in permissions,
            "can_delete_server": Permission.SERVERS_DELETE in permissions,
            
            "can_create_user": Permission.USERS_CREATE in permissions,
            "can_edit_user": Permission.USERS_EDIT in permissions,
            "can_delete_user": Permission.USERS_DELETE in permissions,
            
            "can_edit_profile": Permission.PROFILE_EDIT in permissions,
            "can_export_game": Permission.GAME_EXPORT in permissions,
            
            # Для обратной совместимости
            "show_servers": Permission.SERVERS_VIEW_ALL in permissions,
            "show_users": Permission.USERS_VIEW in permissions,
            "show_my_servers": Permission.MY_SERVERS_VIEW in permissions,
        }


_ui_mapper = UIPermissionMapper()


async def get_ui_flags(
    permissions: Set[Permission] = Depends(get_user_permissions),
) -> dict:
    """
    Получить UI флаги для шаблонов.
    """
    return _ui_mapper.to_ui_flags(permissions)
"""
Зависимости FastAPI для работы с правами доступа.

Эти зависимости позволяют легко добавлять проверку прав в эндпоинты
и получать права пользователя для отображения UI.
"""

from typing import Optional
from fastapi import Depends
from app.auth.models import User
from app.dependencies.auth_dep import get_current_user
from app.services.permissions import PermissionService, UserPermissions
from app.exceptions import ForbiddenException


async def get_current_user_permissions(
    user: Optional[User] = Depends(get_current_user),
) -> UserPermissions:
    """
    Получить права текущего пользователя.
    
    Эта зависимость используется в представлениях для определения,
    какие элементы UI показывать пользователю.
    
    Args:
        user: Текущий пользователь (получается из Depends)
        
    Returns:
        UserPermissions: Права пользователя для UI
    """
    return PermissionService.get_user_permissions(user)


async def require_server_management(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Проверяет, имеет ли пользователь право управлять серверами.
    
    Используется в эндпоинтах, требующих прав модератора или выше.
    Если прав нет, выбрасывает исключение ForbiddenException.
    
    Args:
        user: Текущий пользователь
        
    Returns:
        User: Пользователь, если права есть
        
    Raises:
        ForbiddenException: Если пользователь не имеет прав
    """
    if not PermissionService.can_manage_servers(user):
        raise ForbiddenException("Требуются права модератора для управления серверами")
    return user  # type: ignore


async def require_user_management(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Проверяет, имеет ли пользователь право управлять другими пользователями.
    
    Используется в эндпоинтах, требующих прав администратора.
    Если прав нет, выбрасывает исключение ForbiddenException.
    
    Args:
        user: Текущий пользователь
        
    Returns:
        User: Пользователь, если права есть
        
    Raises:
        ForbiddenException: Если пользователь не имеет прав
    """
    if not PermissionService.can_manage_users(user):
        raise ForbiddenException("Требуются права администратора для управления пользователями")
    return user  # type: ignore


async def require_moderator(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Проверяет, имеет ли пользователь права модератора.
    
    Args:
        user: Текущий пользователь
        
    Returns:
        User: Пользователь, если права есть
        
    Raises:
        ForbiddenException: Если пользователь не модератор
    """
    if not PermissionService.is_moderator_or_admin(user):
        raise ForbiddenException("Требуются права модератора")
    return user  # type: ignore


async def require_admin(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Проверяет, имеет ли пользователь права администратора.
    
    Args:
        user: Текущий пользователь
        
    Returns:
        User: Пользователь, если права есть
        
    Raises:
        ForbiddenException: Если пользователь не администратор
    """
    if not PermissionService.is_admin(user):
        raise ForbiddenException("Требуются права администратора")
    return user  # type: ignore


async def optional_user_permissions(
    user: Optional[User] = Depends(get_current_user),
) -> dict:
    """
    Получить права пользователя в виде словаря для шаблонов.
    
    Упрощенная версия для быстрого использования в представлениях,
    когда не нужен объект UserPermissions.
    
    Returns:
        dict: Словарь с флагами прав для шаблона
    """
    permissions = PermissionService.get_user_permissions(user)
    return permissions.to_dict()
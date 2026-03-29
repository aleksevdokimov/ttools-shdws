"""
Сервис для управления правами доступа пользователей.

Этот сервис централизует всю логику определения прав пользователей,
что позволяет легко тестировать и изменять правила доступа.
"""

from typing import Optional, NamedTuple, Dict, Any
from app.auth.models import User
from app.auth.enums import Role


class UserPermissions(NamedTuple):
    """
    Права пользователя для отображения UI.
    
    Attributes:
        can_view_servers: Может ли пользователь просматривать список всех серверов
        can_manage_users: Может ли пользователь управлять пользователями
        can_view_my_servers: Может ли пользователь просматривать свои серверы
    """
    can_view_servers: bool = False
    can_manage_users: bool = False
    can_view_my_servers: bool = False
    
    def to_dict(self) -> Dict[str, bool]:
        """
        Конвертирует права в словарь для передачи в шаблоны.
        
        Returns:
            Dict[str, bool]: Словарь с флагами для шаблона
        """
        return {
            "show_servers": self.can_view_servers,
            "show_users": self.can_manage_users,
            "show_my_servers": self.can_view_my_servers,
        }
    
    @classmethod
    def empty(cls) -> "UserPermissions":
        """Возвращает пустые права (для неавторизованных пользователей)."""
        return cls()
    
    def has_any_admin_rights(self) -> bool:
        """Есть ли у пользователя какие-либо права администратора."""
        return self.can_view_servers or self.can_manage_users


class PermissionService:
    """
    Сервис для определения прав доступа пользователей.
    
    Этот сервис инкапсулирует всю логику проверки прав,
    основанную на ролях пользователя.
    """
    
    @staticmethod
    def get_user_permissions(user: Optional[User]) -> UserPermissions:
        """
        Получить права пользователя на основе его роли.
        
        Args:
            user: Объект пользователя или None для неавторизованных
            
        Returns:
            UserPermissions: Объект с правами пользователя
        """
        if not user:
            return UserPermissions.empty()
        
        # Проверяем права на основе role_id
        return UserPermissions(
            can_view_servers=Role.is_moderator(user.role_id),
            can_manage_users=Role.is_admin(user.role_id),
            can_view_my_servers=True,  # Все авторизованные пользователи видят свои серверы
        )
    
    @staticmethod
    def can_manage_servers(user: Optional[User]) -> bool:
        """
        Может ли пользователь управлять серверами (создание, редактирование, удаление).
        
        Args:
            user: Объект пользователя или None
            
        Returns:
            bool: True если пользователь может управлять серверами
        """
        return user is not None and Role.is_moderator(user.role_id)
    
    @staticmethod
    def can_manage_users(user: Optional[User]) -> bool:
        """
        Может ли пользователь управлять другими пользователями.
        
        Args:
            user: Объект пользователя или None
            
        Returns:
            bool: True если пользователь может управлять пользователями
        """
        return user is not None and Role.is_admin(user.role_id)
    
    @staticmethod
    def can_view_all_servers(user: Optional[User]) -> bool:
        """
        Может ли пользователь просматривать список всех серверов.
        
        Args:
            user: Объект пользователя или None
            
        Returns:
            bool: True если пользователь может видеть все серверы
        """
        return user is not None and Role.is_moderator(user.role_id)
    
    @staticmethod
    def get_role_name(role_id: int) -> str:
        """
        Получить название роли по её ID.
        
        Args:
            role_id: ID роли
            
        Returns:
            str: Название роли на русском
        """
        return Role.get_name(role_id)
    
    @staticmethod
    def is_moderator_or_admin(user: Optional[User]) -> bool:
        """
        Проверяет, является ли пользователь модератором или администратором.
        
        Args:
            user: Объект пользователя или None
            
        Returns:
            bool: True если пользователь модератор или администратор
        """
        return user is not None and Role.is_moderator(user.role_id)
    
    @staticmethod
    def is_admin(user: Optional[User]) -> bool:
        """
        Проверяет, является ли пользователь администратором.
        
        Args:
            user: Объект пользователя или None
            
        Returns:
            bool: True если пользователь администратор
        """
        return user is not None and Role.is_admin(user.role_id)
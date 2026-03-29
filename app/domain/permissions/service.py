# ============================================================================
# Domain Service
# ============================================================================
from typing import Optional, Set, List
from app.domain.permissions.entities import (
    Permission, Role, UserContext, PermissionProvider
)



class PermissionService:
    """
    Сервис для работы с разрешениями.
    Содержит бизнес-логику, оптимизирован для производительности.
    """
    
    def __init__(self, provider: PermissionProvider):
        self._provider = provider
    
    def get_user_permissions(self, user: Optional[UserContext]) -> Set[Permission]:
        """
        Получить все разрешения пользователя.
        Оптимизировано: суперадмин получает всё без обращения к провайдеру.
        """
        if not user or not user.is_active:
            return set()
        
        # Оптимизация для суперадмина
        if user.is_super_admin:
            # Возвращаем все разрешения без запроса к провайдеру
            return set(Permission)
        
        return self._provider.get_permissions(user.role)
    
    def has_permission(self, user: Optional[UserContext], permission: Permission) -> bool:
        """
        Проверить наличие конкретного разрешения.
        Оптимизировано: сначала проверяем суперадмина.
        """
        if not user or not user.is_active:
            return False
        
        # Суперадмин имеет все разрешения
        if user.is_super_admin:
            return True
        
        return self._provider.has_permission(user.role, permission)
    
    def has_any_permission(self, user: Optional[UserContext], permissions: List[Permission]) -> bool:
        """
        Проверить наличие любого из разрешений.
        Оптимизировано: получаем разрешения один раз, а не для каждого.
        """
        if not user or not user.is_active:
            return False
        
        # Суперадмин имеет все разрешения
        if user.is_super_admin:
            return True
        
        # Получаем все разрешения пользователя один раз
        user_perms = self.get_user_permissions(user)
        
        # Проверяем наличие хотя бы одного
        return any(p in user_perms for p in permissions)
    
    def has_all_permissions(self, user: Optional[UserContext], permissions: List[Permission]) -> bool:
        """
        Проверить наличие всех разрешений.
        Оптимизировано: получаем разрешения один раз, а не для каждого.
        """
        if not user or not user.is_active:
            return False
        
        # Суперадмин имеет все разрешения
        if user.is_super_admin:
            return True
        
        # Получаем все разрешения пользователя один раз
        user_perms = self.get_user_permissions(user)
        
        # Проверяем наличие всех
        return all(p in user_perms for p in permissions)
    
    # Object-level permissions
    def can_manage_server(self, user: UserContext, server_owner_id: str) -> bool:
        """
        Проверка права на управление сервером (object-level).
        """
        # Суперадмин может управлять любым сервером
        if user.is_super_admin:
            return True
        
        # Админ может управлять любым сервером
        if self.has_permission(user, Permission.SERVERS_MANAGE):
            return True
        
        # Обычные пользователи могут управлять только своими серверами
        return user.user_id == server_owner_id
    
    def can_view_user_data(self, user: UserContext, target_user_id: str) -> bool:
        """
        Проверка права на просмотр данных пользователя.
        """
        # Суперадмин видит всех
        if user.is_super_admin:
            return True
        
        # Админ видит всех
        if self.has_permission(user, Permission.USERS_VIEW):
            return True
        
        # Пользователи видят только себя
        return user.user_id == target_user_id
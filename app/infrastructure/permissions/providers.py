"""
Реализации PermissionProvider.
"""

from typing import Set, List
from app.domain.permissions import Permission, Role, PermissionProvider


class StaticPermissionProvider(PermissionProvider):
    """
    Статический провайдер разрешений.
    Это infrastructure, потому что содержит конкретные правила.
    """
    
    # Маппинг ролей на разрешения
    _PERMISSIONS: dict[Role, Set[Permission]] = {
        Role.USER: {
            Permission.MY_SERVERS_VIEW,
            Permission.PROFILE_VIEW,
            Permission.PROFILE_EDIT,
            Permission.GAME_VIEW,
            Permission.API_KEYS_MANAGE,
        },
        Role.MODERATOR: {
            Permission.MY_SERVERS_VIEW,
            Permission.PROFILE_VIEW,
            Permission.PROFILE_EDIT,
            Permission.GAME_VIEW,
            Permission.API_KEYS_MANAGE,
            Permission.SERVERS_VIEW_ALL,
            Permission.SERVERS_MANAGE,
            Permission.GAME_EXPORT,
        },
        Role.ADMIN: {
            Permission.MY_SERVERS_VIEW,
            Permission.PROFILE_VIEW,
            Permission.PROFILE_EDIT,
            Permission.GAME_VIEW,
            Permission.API_KEYS_MANAGE,
            Permission.SERVERS_VIEW_ALL,
            Permission.SERVERS_MANAGE,
            Permission.SERVERS_DELETE,
            Permission.USERS_VIEW,
            Permission.USERS_CREATE,
            Permission.USERS_EDIT,
            Permission.USERS_DELETE,
            Permission.KEYS_VIEW,
            Permission.KEYS_CREATE,
            Permission.KEYS_DELETE,
            Permission.GAME_EXPORT,
            Permission.AUDIT_VIEW,
        },
        # SUPER_ADMIN обрабатывается отдельно в сервисе для производительности
        # Поэтому здесь его нет
    }
    
    # Обратный индекс для быстрого поиска
    _PERMISSION_TO_ROLES: dict[Permission, List[Role]] = {}
    
    def __init__(self):
        """Строим обратный индекс при инициализации."""
        for role, perms in self._PERMISSIONS.items():
            for perm in perms:
                if perm not in self._PERMISSION_TO_ROLES:
                    self._PERMISSION_TO_ROLES[perm] = []
                self._PERMISSION_TO_ROLES[perm].append(role)
    
    def get_permissions(self, role: Role) -> Set[Permission]:
        """Получить разрешения для роли."""
        return self._PERMISSIONS.get(role, set()).copy()
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Проверить наличие разрешения."""
        return permission in self._PERMISSIONS.get(role, set())
    
    def get_roles_with_permission(self, permission: Permission) -> List[Role]:
        """Получить роли, имеющие разрешение."""
        return self._PERMISSION_TO_ROLES.get(permission, [])
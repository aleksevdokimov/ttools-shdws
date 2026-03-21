from enum import IntEnum


class Role(IntEnum):
    """Перечисление ролей пользователей."""
    USER = 1
    MODERATOR = 2
    ADMIN = 3
    
    @classmethod
    def get_name(cls, value: int) -> str:
        """Получить название роли по её ID."""
        names = {
            1: "Пользователь",
            2: "Модератор", 
            3: "Администратор"
        }
        return names.get(value, "Пользователь")
    
    @classmethod
    def is_admin(cls, role_id: int) -> bool:
        """Проверить, является ли роль администратором (ADMIN или SUPERADMIN)."""
        return role_id in [cls.ADMIN]
    
    @classmethod
    def is_moderator(cls, role_id: int) -> bool:
        """Проверить, является ли роль модератором (MODERATOR, ADMIN или SUPERADMIN)."""
        return role_id in [cls.MODERATOR, cls.ADMIN]

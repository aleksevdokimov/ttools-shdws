# app/infrastructure/permissions/mapper.py
"""
Мапперы для конвертации между инфраструктурой и доменом.
"""

from app.auth.models import User
from app.domain.permissions import Role, UserContext
# from app.auth.enums import Role as RoleEnum


class UserContextMapper:
    """
    Маппер для создания UserContext из ORM модели.
    Изолирует domain от деталей БД.
    """
    
    # Маппинг ID ролей из БД в domain роли
    _ROLE_ID_MAPPING = {
        1: Role.USER,
        2: Role.MODERATOR,
        4: Role.ADMIN,
        # 8: Role.SUPER_ADMIN,
    }
    
    @classmethod
    def from_orm(cls, user: User) -> UserContext:
        """
        Преобразует ORM модель в domain объект.
        Здесь происходит вся магия конвертации ID -> Role.
        """
        role = cls._ROLE_ID_MAPPING.get(user.role_id, Role.USER)
        
        return UserContext(
            user_id=str(user.id),  # Конвертируем в строку для domain
            role=role,
            is_active=user.is_active,
        )
    
    @classmethod
    def to_role_id(cls, role: Role) -> int:
        """
        Обратное преобразование domain роли в ID для БД.
        """
        reverse_mapping = {v: k for k, v in cls._ROLE_ID_MAPPING.items()}
        return reverse_mapping.get(role, 1)

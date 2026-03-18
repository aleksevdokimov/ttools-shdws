from datetime import datetime
from typing import Tuple
from app.dao.base import BaseDAO
from app.auth.models import User, Role


class UsersDAO(BaseDAO):
    model = User

    async def find_paginated_with_filters(
        self,
        page: int = 1,
        per_page: int = 10,
        username: str | None = None,
        email: str | None = None,
        is_active: bool | None = None,
    ) -> Tuple[list[User], int]:
        """
        Пагинированный поиск пользователей с фильтрами.
        
        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество записей на странице
            username: Фильтр по логину (частичное совпадение)
            email: Фильтр по email (частичное совпадение)
            is_active: Фильтр по активности
            
        Returns:
            Кортеж (список пользователей, общее количество)
        """
        # Формируем фильтры
        filters = {}
        if username:
            filters['username'] = f"%{username}%"
        if email:
            filters['email'] = f"%{email}%"
        if is_active is not None:
            filters['is_active'] = is_active
        
        # Получаем общее количество с фильтрами
        total = await self.count_with_filters(filters)
        
        # Получаем пользователей
        users = await self.find_paginated(
            page=page,
            per_page=per_page,
            filters=filters,
            order_by='id',
            order_desc=True
        )
        
        return users, total

    async def soft_delete(self, user_id: int) -> int:
        """
        Мягкое удаление пользователя (устанавливает deleted_at).
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество обновлённых записей
        """
        from sqlalchemy import update
        from sqlalchemy.sql import literal_column
        
        stmt = (
            update(self.model)
            .where(self.model.id == user_id)
            .values(deleted_at=datetime.now().isoformat())
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def restore(self, user_id: int) -> int:
        """
        Восстановление пользователя (удаляет deleted_at).
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество обновлённых записей
        """
        from sqlalchemy import update
        
        stmt = (
            update(self.model)
            .where(self.model.id == user_id)
            .values(deleted_at=None)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount


class RoleDAO(BaseDAO):
    model = Role
    
    async def find_all_roles(self):
        """Получить все роли."""
        return await self.find_all()
    
    async def find_role_by_id(self, role_id: int):
        """Получить роль по ID."""
        return await self.find_one_or_none_by_id(role_id)

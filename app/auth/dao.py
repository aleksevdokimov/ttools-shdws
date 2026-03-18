import secrets
from datetime import datetime
from typing import Tuple
from app.dao.base import BaseDAO
from app.auth.models import User, Role, RegistrationToken


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

    async def find_role_by_id(self, role_id: int):
        """Получить роль по ID."""
        return await self.find_one_or_none_by_id(role_id)

    async def find_all_roles(self):
        """Получить все роли."""
        return await self.find_all()


class RegistrationTokensDAO(BaseDAO):
    model = RegistrationToken

    async def get_valid_token(self, token: str) -> RegistrationToken | None:
        """
        Получить валидный токен по строке токена.
        Токен валиден если: существует, used_by_user_id IS NULL,
        expires_at NULL или > NOW().
        """
        from sqlalchemy import select

        stmt = select(self.model).where(
            self.model.token == token,
            self.model.used_by_user_id.is_(None),
            (self.model.expires_at.is_(None) | (self.model.expires_at > datetime.utcnow()))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_tokens(self, count: int = 10) -> list[RegistrationToken]:
        """
        Сгенерировать указанное количество новых токенов.
        """
        tokens = []
        for _ in range(count):
            token_str = secrets.token_hex(16)  # 32 символа
            token = RegistrationToken(token=token_str)
            tokens.append(token)
            self._session.add(token)
        await self._session.flush()
        return tokens

    async def find_paginated_with_filters(
        self,
        page: int = 1,
        per_page: int = 10,
        token: str | None = None,
        used: bool | None = None,
    ) -> Tuple[list[RegistrationToken], int]:
        """
        Пагинированный поиск токенов с фильтрами.

        Args:
            page: Номер страницы
            per_page: Записей на странице
            token: Фильтр по токену (частичное совпадение)
            used: Фильтр по использованию (True - использованные, False - неиспользованные)

        Returns:
            Кортеж (список токенов, общее количество)
        """
        filters = {}
        if token:
            filters['token'] = f"%{token}%"
        if used is not None:
            if used:
                filters['used_by_user_id'] = 'NOT NULL'
            else:
                filters['used_by_user_id'] = 'NULL'

        total = await self.count_with_filters(filters)
        tokens = await self.find_paginated(
            page=page,
            per_page=per_page,
            filters=filters,
            order_by='id',
            order_desc=True
        )
        return tokens, total

    async def mark_used(self, token_id: int, user_id: int) -> bool:
        """
        Пометить токен как использованный.
        """
        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(self.model.id == token_id)
            .values(used_by_user_id=user_id, used_at=datetime.utcnow())
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

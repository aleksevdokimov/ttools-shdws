from datetime import datetime
from typing import Tuple
from sqlalchemy import func
from app.dao.base import BaseDAO
from app.game.models import Server, UserServer, Player, TypeField, MapCell, MapFeature, Village, PlayerVerification, ApiKey
from app.game.schemas import UserServerCreate


class ServerDAO(BaseDAO):
    model = Server

    async def find_paginated_with_filters(
        self,
        page: int = 1,
        per_page: int = 10,
        name: str | None = None,
        is_active: bool | None = None,
        is_deleted: bool | None = None,
    ) -> Tuple[list[Server], int]:
        """
        Пагинированный поиск серверов с фильтрами.
        
        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество записей на странице
            name: Фильтр по названию (частичное совпадение)
            is_active: Фильтр по активности
            is_deleted: Фильтр по удалению (True - только удалённые, False - только неудалённые, None - все)
            
        Returns:
            Кортеж (список серверов, общее количество)
        """
        from sqlalchemy import select, or_, and_, func
        
        # Формируем фильтры
        filters = {}
        if name:
            filters['name'] = f"%{name}%"
        if is_active is not None:
            filters['is_active'] = is_active
        
        # Базовая часть запроса
        query = select(self.model)
        
        # Применяем фильтры
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, str) and '%' in value:
                        filter_conditions.append(
                            getattr(self.model, key).like(value)
                        )
                    else:
                        filter_conditions.append(
                            getattr(self.model, key) == value
                        )
            if filter_conditions:
                query = query.where(*filter_conditions)
        
        # Фильтр по deleted_at
        if is_deleted is True:
            query = query.where(self.model.deleted_at.isnot(None))
        elif is_deleted is False:
            query = query.where(self.model.deleted_at.is_(None))
        
        # Получаем общее количество
        count_query = select(func.count(self.model.id))
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, str) and '%' in value:
                        filter_conditions.append(
                            getattr(self.model, key).like(value)
                        )
                    else:
                        filter_conditions.append(
                            getattr(self.model, key) == value
                        )
            if filter_conditions:
                count_query = count_query.where(*filter_conditions)
        
        if is_deleted is True:
            count_query = count_query.where(self.model.deleted_at.isnot(None))
        elif is_deleted is False:
            count_query = count_query.where(self.model.deleted_at.is_(None))
        
        total_result = await self._session.execute(count_query)
        total = total_result.scalar()
        
        # Получаем серверы
        servers = await self.find_paginated(
            page=page,
            per_page=per_page,
            filters=filters,
            order_by='id',
            order_desc=True
        )
        
        return servers, total

    async def find_paginated_with_deleted(
        self,
        page: int = 1,
        per_page: int = 10,
        name: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> Tuple[list[Server], int]:
        """
        Пагинированный поиск серверов с возможностью включения удалённых.
        
        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество записей на странице
            name: Фильтр по названию (частичное совпадение)
            is_active: Фильтр по активности
            include_deleted: Включить удалённые записи
            
        Returns:
            Кортеж (список серверов, общее количество)
        """
        from sqlalchemy import select, or_, and_
        
        # Формируем фильтры
        filters = {}
        if name:
            filters['name'] = f"%{name}%"
        if is_active is not None:
            filters['is_active'] = is_active
        
        # Базовая часть запроса
        query = select(self.model)
        
        # Применяем фильтры
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, str) and '%' in value:
                        filter_conditions.append(
                            getattr(self.model, key).like(value)
                        )
                    else:
                        filter_conditions.append(
                            getattr(self.model, key) == value
                        )
            if filter_conditions:
                query = query.where(*filter_conditions)
        
        # Фильтр по deleted_at
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        
        # Получаем общее количество
        from sqlalchemy import func
        count_query = select(func.count(self.model.id))
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, str) and '%' in value:
                        filter_conditions.append(
                            getattr(self.model, key).like(value)
                        )
                    else:
                        filter_conditions.append(
                            getattr(self.model, key) == value
                        )
            if filter_conditions:
                count_query = count_query.where(*filter_conditions)
        
        if not include_deleted:
            count_query = count_query.where(self.model.deleted_at.is_(None))
        
        total_result = await self._session.execute(count_query)
        total = total_result.scalar()
        
        # Сортировка и пагинация
        query = query.order_by(self.model.id.desc())
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await self._session.execute(query)
        servers = result.scalars().all()
        
        return servers, total

    async def soft_delete(self, server_id: int) -> int:
        """
        Мягкое удаление сервера (устанавливает deleted_at).
        
        Args:
            server_id: ID сервера
            
        Returns:
            Количество обновлённых записей
        """
        from sqlalchemy import update
        
        stmt = (
            update(self.model)
            .where(self.model.id == server_id)
            .values(deleted_at=datetime.now())
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def restore(self, server_id: int) -> int:
        """
        Восстановление сервера (удаляет deleted_at).
        
        Args:
            server_id: ID сервера
            
        Returns:
            Количество обновлённых записей
        """
        from sqlalchemy import update
        
        stmt = (
            update(self.model)
            .where(self.model.id == server_id)
            .values(deleted_at=None)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount


class UserServerDAO(BaseDAO):
    """DAO для работы со связями пользователей и серверами."""
    model = UserServer

    async def find_by_user(self, user_id: int) -> list[UserServer]:
        """
        Получить все серверы пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список связей пользователя с серверами
        """
        from sqlalchemy import select

        stmt = select(self.model).where(self.model.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_active(self, user_id: int) -> UserServer | None:
        """
        Получить активный сервер пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Активная связь или None
        """
        from sqlalchemy import select

        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_active == True
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_active(self, user_id: int, server_id: int) -> None:
        """
        Установить активный сервер для пользователя.
        Сначала сбрасывает все is_active в False, затем устанавливает указанный.

        Args:
            user_id: ID пользователя
            server_id: ID сервера
        """
        from sqlalchemy import update

        # Сбрасываем все активные
        stmt = (
            update(self.model)
            .where(self.model.user_id == user_id)
            .values(is_active=False)
        )
        await self._session.execute(stmt)

        # Устанавливаем новый активный
        stmt = (
            update(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.server_id == server_id
            )
            .values(is_active=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def unset_active(self, user_id: int, server_id: int) -> None:
        """
        Снять активность с сервера для пользователя.

        Args:
            user_id: ID пользователя
            server_id: ID сервера
        """
        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.server_id == server_id
            )
            .values(is_active=False)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def add_user_server(self, user_id: int, server_id: int) -> UserServer:
        """
        Добавить сервер пользователю.

        Args:
            user_id: ID пользователя
            server_id: ID сервера

        Returns:
            Созданная связь
        """
        # Проверяем, не существует ли уже
        existing = await self.find_by_user(user_id)
        for us in existing:
            if us.server_id == server_id:
                return us

        return await self.add(values=UserServerCreate(
            user_id=user_id,
            server_id=server_id,
            is_active=len(existing) == 0  # Первый сервер становится активным
        ))

    async def remove_user_server(self, user_id: int, server_id: int) -> bool:
        """
        Удалить сервер у пользователя.

        Args:
            user_id: ID пользователя
            server_id: ID сервера

        Returns:
            True если удалено
        """
        from sqlalchemy import delete

        stmt = delete(self.model).where(
            self.model.user_id == user_id,
            self.model.server_id == server_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        # Если удалён активный сервер, устанавливаем первый попавшийся активным
        if result.rowcount > 0:
            remaining = await self.find_by_user(user_id)
            if remaining and not any(us.is_active for us in remaining):
                remaining[0].is_active = True
                await self._session.flush()

        return result.rowcount > 0


class MapDAO(BaseDAO):
    """DAO для комплексных операций с картой."""
    model = MapCell  # Фиктивная модель для BaseDAO

    async def search_cells(
        self,
        server_id: int,
        type_ids: list[int] | None = None,
        min_crop: int = 0,
        min_wood: int = 0,
        min_clay: int = 0,
        min_iron: int = 0,
        occupied: bool | None = None,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[dict], int]:
        """
        Поиск клеток карты с фильтрами.

        Args:
            server_id: ID сервера
            type_ids: Список ID типов клеток
            min_crop, min_wood, min_clay, min_iron: Минимальные бонусы оазисов
            occupied: True-занятые, False-свободные, None-все
            page: Номер страницы
            per_page: Количество на страницу

        Returns:
            Кортеж (список клеток, общее количество)
        """
        from sqlalchemy import select, func, and_, or_
        from app.game.models import Village

        # Базовый запрос с JOIN
        query = select(
            MapCell.x,
            MapCell.y,
            MapCell.type_id,
            TypeField.name.label('type_name'),
            MapFeature.oasis_crop,
            MapFeature.oasis_wood,
            MapFeature.oasis_clay,
            MapFeature.oasis_iron,
            func.coalesce(Village.name, None).label('village_name'),
            func.coalesce(Village.player_id, None).label('village_player_id')
        ).select_from(MapCell).join(
            TypeField, MapCell.type_id == TypeField.id
        ).outerjoin(
            MapFeature, and_(
                MapFeature.server_id == MapCell.server_id,
                MapFeature.x == MapCell.x,
                MapFeature.y == MapCell.y
            )
        ).outerjoin(
            Village, and_(
                Village.server_id == MapCell.server_id,
                Village.x == MapCell.x,
                Village.y == MapCell.y
            )
        ).where(MapCell.server_id == server_id)

        # Фильтры по типам
        if type_ids:
            query = query.where(MapCell.type_id.in_(type_ids))
        else:
            # По умолчанию фильтровать типы с id >= 9 and id <= 20
            query = query.where(MapCell.type_id.between(9, 20))

        # Фильтры по бонусам оазисов
        if min_crop > 0:
            query = query.where(func.coalesce(MapFeature.oasis_crop, 0) >= min_crop)
        if min_wood > 0:
            query = query.where(func.coalesce(MapFeature.oasis_wood, 0) >= min_wood)
        if min_clay > 0:
            query = query.where(func.coalesce(MapFeature.oasis_clay, 0) >= min_clay)
        if min_iron > 0:
            query = query.where(func.coalesce(MapFeature.oasis_iron, 0) >= min_iron)

        # Фильтр по занятости
        if occupied is True:
            query = query.where(Village.id.isnot(None))
        elif occupied is False:
            query = query.where(Village.id.is_(None))

        # Получаем общее количество
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar()

        # Пагинация и сортировка
        offset = (page - 1) * per_page
        query = query.order_by(MapCell.x, MapCell.y).offset(offset).limit(per_page)

        result = await self._session.execute(query)
        rows = result.all()

        # Преобразуем в список словарей
        cells = []
        for row in rows:
            cells.append({
                'x': row.x,
                'y': row.y,
                'type_id': row.type_id,
                'type_name': row.type_name.replace('Field ', '', 1) if row.type_name.startswith('Field ') else row.type_name,
                'oasis_crop': row.oasis_crop,
                'oasis_wood': row.oasis_wood,
                'oasis_clay': row.oasis_clay,
                'oasis_iron': row.oasis_iron,
                'occupied': row.village_name is not None,
                'occupied_by': row.village_name or None
            })

        return cells, total

    async def get_map_area(self, server_id: int, center_x: int, center_y: int) -> list[dict]:
        """
        Получить область карты 21x21 вокруг центра.

        Args:
            server_id: ID сервера
            center_x, center_y: Координаты центра

        Returns:
            Список клеток области
        """
        from sqlalchemy import select, and_, or_

        # Получить размер сервера
        server_query = select(Server.settings).where(Server.id == server_id)
        server_result = await self._session.execute(server_query)
        server_row = server_result.first()
        if not server_row:
            return []
        size = int(server_row[0].get('Size', 400))

        # Функция нормализации
        def normalize_coord(coord):
            while coord > size:
                coord -= 2 * size + 1
            while coord < -size:
                coord += 2 * size + 1
            return coord

        # Собрать список реальных координат
        coords = []
        for dx in range(-10, 11):
            for dy in range(-10, 11):
                real_x = normalize_coord(center_x + dx)
                real_y = normalize_coord(center_y + dy)
                coords.append((real_x, real_y))

        # Создать запросы для каждой координаты и объединить union
        subqueries = []
        for x, y in coords:
            subq = select(
                MapCell.x.label('x'),
                MapCell.y.label('y'),
                MapCell.type_id.label('type_id'),
                TypeField.name.label('type_name'),
                (MapFeature.oasis_crop.isnot(None) | MapFeature.oasis_wood.isnot(None) | MapFeature.oasis_clay.isnot(None) | MapFeature.oasis_iron.isnot(None)).label('has_oasis')
            ).select_from(MapCell).join(
                TypeField, TypeField.id == MapCell.type_id
            ).outerjoin(
                MapFeature, and_(
                    MapFeature.server_id == MapCell.server_id,
                    MapFeature.x == MapCell.x,
                    MapFeature.y == MapCell.y
                )
            ).where(
                MapCell.server_id == server_id,
                MapCell.x == x,
                MapCell.y == y
            )
            subqueries.append(subq)

        if not subqueries:
            return []

        # Объединить все subqueries с union
        from sqlalchemy import union_all
        query = union_all(*subqueries).order_by('x', 'y')

        result = await self._session.execute(query)
        rows = result.all()

        # Преобразуем в список словарей
        cells = []
        for row in rows:
            cells.append({
                'x': row.x,
                'y': row.y,
                'type_id': row.type_id,
                'type_name': row.type_name,
                'has_oasis': row.has_oasis
            })

        return cells


class PlayerDAO(BaseDAO):
    """DAO для работы с игроками."""
    model = Player

    async def find_by_user_and_server(self, user_id: int, server_id: int) -> Player | None:
        """
        Найти игрока по user_id и server_id.
        
        Args:
            user_id: ID пользователя
            server_id: ID сервера
            
        Returns:
            Игрок или None
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.server_id == server_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_server(self, server_id: int) -> list[Player]:
        """
        Найти всех игроков сервера.
        
        Args:
            server_id: ID сервера
            
        Returns:
            Список игроков
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(self.model.server_id == server_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class TypeFieldDAO(BaseDAO):
    """DAO для работы с типами полей карты."""
    model = TypeField

    async def find_by_name(self, name: str) -> TypeField | None:
        """
        Получить тип поля по имени.
        
        Args:
            name: Название типа поля
            
        Returns:
            Тип поля или None
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(self.model.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, **kwargs) -> TypeField:
        """
        Получить или создать тип поля.
        
        Args:
            name: Название типа поля
            **kwargs: Дополнительные поля
            
        Returns:
            Тип поля
        """
        existing = await self.find_by_name(name)
        if existing:
            return existing
        return await self.add(values=self.model(name=name, **kwargs))


class MapCellDAO(BaseDAO):
    """DAO для работы с ячейками карты."""
    model = MapCell

    async def find_by_coords(self, server_id: int, x: int, y: int) -> MapCell | None:
        """
        Получить ячейку карты по координатам.
        
        Args:
            server_id: ID сервера
            x: Координата X
            y: Координата Y
            
        Returns:
            Ячейка карты или None
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(
            self.model.server_id == server_id,
            self.model.x == x,
            self.model.y == y
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_server(self, server_id: int) -> list[MapCell]:
        """
        Получить все ячейки карты для сервера.
        
        Args:
            server_id: ID сервера
            
        Returns:
            Список ячеек карты
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(self.model.server_id == server_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, cells_data: list[dict]) -> list[MapCell]:
        """
        Массовое создание ячеек карты.
        
        Args:
            cells_data: Список данных для создания ячеек
            
        Returns:
            Список созданных ячеек
        """
        from sqlalchemy import select, insert
        
        if not cells_data:
            return []
        
        stmt = insert(self.model).values(cells_data)
        await self._session.execute(stmt)
        await self._session.flush()
        # Получаем созданные записи
        server_id = cells_data[0]['server_id']
        stmt = select(self.model).where(self.model.server_id == server_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class MapFeatureDAO(BaseDAO):
    """DAO для работы с особенностями карты."""
    model = MapFeature

    async def find_by_coords(self, server_id: int, x: int, y: int) -> MapFeature | None:
        """
        Получить особенности карты по координатам.

        Args:
            server_id: ID сервера
            x: Координата X
            y: Координата Y

        Returns:
            Особенности карты или None
        """
        from sqlalchemy import select

        stmt = select(self.model).where(
            self.model.server_id == server_id,
            self.model.x == x,
            self.model.y == y
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_server(self, server_id: int) -> list[MapFeature]:
        """
        Получить все особенности карты для сервера.

        Args:
            server_id: ID сервера

        Returns:
            Список особенностей карты
        """
        from sqlalchemy import select

        stmt = select(self.model).where(self.model.server_id == server_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, features_data: list[dict]) -> list[MapFeature]:
        """
        Массовое создание особенностей карты.

        Args:
            features_data: Список данных для создания особенностей

        Returns:
            Список созданных особенностей
        """
        from sqlalchemy import select, insert

        if not features_data:
            return []

        stmt = insert(self.model).values(features_data)
        await self._session.execute(stmt)
        await self._session.flush()

        # Получаем созданные записи
        server_id = features_data[0]['server_id']
        stmt = select(self.model).where(self.model.server_id == server_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class PlayerVerificationDAO(BaseDAO):
    """DAO для работы с подтверждениями игроков."""
    model = PlayerVerification

    async def find_by_user_and_player(
        self, 
        user_id: int, 
        player_id: int,
        server_id: int
    ) -> PlayerVerification | None:
        """
        Найти подтверждение по пользователю и игроку.
        
        Args:
            user_id: ID пользователя
            player_id: ID игрока
            server_id: ID сервера
            
        Returns:
            Запись подтверждения или None
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.player_id == player_id,
            self.model.server_id == server_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_user_and_server(
        self, 
        user_id: int, 
        server_id: int
    ) -> list[PlayerVerification]:
        """
        Найти все подтверждения пользователя на сервере.
        
        Args:
            user_id: ID пользователя
            server_id: ID сервера
            
        Returns:
            Список записей подтверждений
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.server_id == server_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_or_update(
        self,
        user_id: int,
        player_id: int,
        server_id: int,
        verification_code: str
    ) -> PlayerVerification:
        """
        Создать или обновить подтверждение.
        
        Args:
            user_id: ID пользователя
            player_id: ID игрока
            server_id: ID сервера
            verification_code: Новый код подтверждения
            
        Returns:
            Запись подтверждения
        """
        from app.game.models import PlayerVerification as PV
        from datetime import datetime
        
        existing = await self.find_by_user_and_player(user_id, player_id, server_id)
        
        if existing:
            # Обновляем существующую запись
            existing.verification_code = verification_code
            existing.is_verified = False
            existing.verified_at = None
            await self._session.flush()
            return existing
        else:
            # Создаём новую запись напрямую через ORM
            new_verification = PV(
                user_id=user_id,
                player_id=player_id,
                server_id=server_id,
                verification_code=verification_code,
                is_verified=False
            )
            self._session.add(new_verification)
            await self._session.flush()
            return new_verification

    async def verify(
        self,
        user_id: int,
        player_id: int,
        server_id: int,
        code: str
    ) -> bool:
        """
        Подтвердить игрока по коду.
        
        Args:
            user_id: ID пользователя
            player_id: ID игрока
            server_id: ID сервера
            code: Код подтверждения
            
        Returns:
            True если успешно подтверждён
        """
        from sqlalchemy import update
        from datetime import datetime
        from app.game.models import Player
        
        stmt = (
            update(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.player_id == player_id,
                self.model.server_id == server_id,
                self.model.verification_code == code,
                self.model.is_verified == False
            )
            .values(
                is_verified=True,
                verified_at=datetime.utcnow()
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        
        if result.rowcount > 0:
            # Обновляем is_verified в модели Player
            player_stmt = (
                update(Player)
                .where(Player.id == player_id)
                .values(is_verified=True)
            )
            await self._session.execute(player_stmt)
            await self._session.flush()
            return True
        
        return False
    
    async def delete_by_id(self, verification_id: int) -> bool:
        """
        Удалить запись подтверждения по ID.
        
        Args:
            verification_id: ID записи
            
        Returns:
            True если удалено
        """
        from sqlalchemy import delete
        
        stmt = delete(self.model).where(self.model.id == verification_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0


class ApiKeyDAO(BaseDAO):
    """DAO для работы с API ключами."""
    model = ApiKey

    async def find_by_player_and_server(
        self, 
        player_id: int, 
        server_id: int,
        only_active: bool = True
    ) -> ApiKey | None:
        """
        Найти API ключ по игроку и серверу.
        
        Args:
            player_id: ID игрока
            server_id: ID сервера
            only_active: Только активные ключи
            
        Returns:
            API ключ или None
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(
            self.model.player_id == player_id,
            self.model.server_id == server_id
        )
        
        if only_active:
            stmt = stmt.where(self.model.is_active == True)
        
        stmt = stmt.order_by(self.model.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_active_by_player(self, player_id: int) -> list[ApiKey]:
        """
        Найти все активные ключи игрока.
        
        Args:
            player_id: ID игрока
            
        Returns:
            Список API ключей
        """
        from sqlalchemy import select
        
        stmt = select(self.model).where(
            self.model.player_id == player_id,
            self.model.is_active == True
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_all_for_player(self, player_id: int, server_id: int) -> int:
        """
        Деактивировать все ключи игрока на сервере.
        
        Args:
            player_id: ID игрока
            server_id: ID сервера
            
        Returns:
            Количество деактивированных ключей
        """
        from sqlalchemy import update
        
        stmt = (
            update(self.model)
            .where(
                self.model.player_id == player_id,
                self.model.server_id == server_id
            )
            .values(is_active=False)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def create_key(
        self, 
        player_id: int, 
        server_id: int,
        key_value: str
    ) -> ApiKey:
        """
        Создать новый API ключ, предварительно деактивируя старые.
        
        Args:
            player_id: ID игрока
            server_id: ID сервера
            key_value: Значение ключа
            
        Returns:
            Созданный API ключ
        """
        # Деактивируем старые ключи
        await self.deactivate_all_for_player(player_id, server_id)
        
        new_key = ApiKey(
            player_id=player_id,
            server_id=server_id,
            key_value=key_value,
            is_active=True
        )
        self._session.add(new_key)
        await self._session.flush()
        return new_key
  
  

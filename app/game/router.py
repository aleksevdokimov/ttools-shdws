from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.auth.models import User
from app.auth.enums import Role
from app.dependencies.auth_dep import get_current_user
from app.dependencies.dao_dep import get_session_with_commit, get_session_without_commit
from app.game.dao import ServerDAO, UserServerDAO, PlayerDAO, MapDAO
from app.game.models import Server
from app.game.schemas import (
    ServerCreate, ServerUpdate, ServerResponse, UserServerResponse,
    MapUpdateResponse, MapUpdateRequest, ServerUpdateResponse, UpdateAllResponse,
    MapCellFilterRequest, MapCellSearchResponse, MapAreaResponse
)
from app.exceptions import UserNotFoundException, ServerAlreadyExistsException, ForbiddenException, ServerUrlAlreadyExistsException, ServerNotFoundException, UserServerNotFoundException
from app.services.scheduler import scheduler
from app.services.map_update import map_update_service


router = APIRouter()


class ServerListResponse(BaseModel):
    """Схема ответа со списком серверов."""
    servers: List[ServerResponse]
    total: int
    page: int
    per_page: int
    pages: int


async def _check_admin_or_moderator(user: User = Depends(get_current_user)) -> User:
    """Проверяет права администратора или модератора."""
    if not Role.is_moderator(user.role_id):
        raise ForbiddenException
    return user


# Эндпоинты для управления серверами

@router.get("/servers/", response_model=ServerListResponse)
async def get_servers(
    page: int = 1,
    per_page: int = 10,
    name: str | None = None,
    is_active: str | None = None,
    is_deleted: str | None = None,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(_check_admin_or_moderator)
) -> ServerListResponse:
    """
    Получение списка серверов с пагинацией и фильтрацией.
    Доступно для Админа (id=3) и Модератора (id=2).
    """
    # Преобразуем is_active из строки в bool
    is_active_bool = None
    if is_active is not None and is_active != '':
        is_active_bool = is_active.lower() == 'true'
    
    # Преобразуем is_deleted из строки в bool
    is_deleted_bool = None
    if is_deleted is not None and is_deleted != '':
        is_deleted_bool = is_deleted.lower() == 'true'
    
    server_dao = ServerDAO(session)
    servers, total = await server_dao.find_paginated_with_filters(
        page=page,
        per_page=per_page,
        name=name,
        is_active=is_active_bool,
        is_deleted=is_deleted_bool
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return ServerListResponse(
        servers=[ServerResponse.model_validate(s) for s in servers],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("/servers/", response_model=ServerResponse)
async def create_server(
    server_data: ServerCreate,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(_check_admin_or_moderator)
) -> ServerResponse:
    """
    Создание нового сервера.
    Доступно для Админа (id=3) и Модератора (id=2).
    """
    server_dao = ServerDAO(session)
    
    # Проверка существования сервера по названию
    from sqlalchemy import select
    stmt = select(server_dao.model).where(server_dao.model.name == server_data.name)
    result = await session.execute(stmt)
    existing_server = result.scalar_one_or_none()
    if existing_server:
        raise ServerAlreadyExistsException
    
    # Проверка существования сервера по URL
    stmt = select(server_dao.model).where(server_dao.model.url == server_data.url)
    result = await session.execute(stmt)
    existing_url = result.scalar_one_or_none()
    if existing_url:
        raise ServerUrlAlreadyExistsException
    
    new_server = await server_dao.add(values=server_data)
    
    return ServerResponse.model_validate(new_server)


@router.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(_check_admin_or_moderator)
) -> ServerResponse:
    """
    Получение сервера по ID.
    Доступно для Админа (id=3) и Модератора (id=2).
    """
    server_dao = ServerDAO(session)
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    return ServerResponse.model_validate(server)


@router.patch("/servers/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    server_data: ServerUpdate,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(_check_admin_or_moderator)
) -> ServerResponse:
    """
    Обновление сервера.
    Доступно для Админа (id=3) и Модератора (id=2).
    """
    server_dao = ServerDAO(session)
    
    # Проверяем существование сервера
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    
    # Подготовка данных для обновления
    update_dict = server_data.model_dump(exclude_unset=True)
    
    # Проверка уникальности названия
    if 'name' in update_dict and update_dict['name'] != server.name:
        from sqlalchemy import select
        stmt = select(server_dao.model).where(server_dao.model.name == update_dict['name'])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing and existing.id != server_id:
            raise ServerAlreadyExistsException
    
    # Проверка уникальности URL
    if 'url' in update_dict and update_dict['url'] != server.url:
        from sqlalchemy import select
        stmt = select(server_dao.model).where(server_dao.model.url == update_dict['url'])
        result = await session.execute(stmt)
        existing_url = result.scalar_one_or_none()
        if existing_url and existing_url.id != server_id:
            raise ServerUrlAlreadyExistsException
    
    # Обновляем сервер
    update_values = {k: v for k, v in update_dict.items() if v is not None}
    from sqlalchemy import update
    stmt = (
        update(server_dao.model)
        .where(server_dao.model.id == server_id)
        .values(**update_values)
    )
    await session.execute(stmt)
    await session.flush()
    
    # Получаем обновлённого сервера
    updated_server = await server_dao.find_one_or_none_by_id(server_id)
    return ServerResponse.model_validate(updated_server)


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(_check_admin_or_moderator)
) -> dict:
    """
    Мягкое удаление сервера.
    Доступно для Админа (id=3) и Модератора (id=2).
    """
    server_dao = ServerDAO(session)
    
    # Проверяем существование сервера
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    
    # Мягкое удаление
    await server_dao.soft_delete(server_id)
    return {"message": "Сервер успешно удалён"}


@router.post("/servers/{server_id}/restore")
async def restore_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(_check_admin_or_moderator)
) -> dict:
    """
    Восстановление удалённого сервера.
    Доступно для Админа (id=3) и Модератора (id=2).
    """
    server_dao = ServerDAO(session)
    
    # Проверяем существование сервера
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    
    # Восстановление
    await server_dao.restore(server_id)
    return {"message": "Сервер успешно восстановлен"}


# === Эндпоинты для пользовательских серверов ===

class UserServerWithDetails(BaseModel):
    """Схема сервера с деталями для пользователя."""
    id: int
    server_id: int
    server_name: str
    server_url: str
    server_speed: str
    is_active: bool
    player_name: str | None = None
    player_verified: bool = False


class ActiveServerResponse(BaseModel):
    """Схема активного сервера для добавления."""
    id: int
    name: str
    url: str
    speed: str


@router.get("/servers/active/", response_model=List[ActiveServerResponse])
async def get_active_servers(
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> List[ActiveServerResponse]:
    """
    Получение списка активных серверов для добавления пользователем.
    Доступно для всех авторизованных пользователей.
    """
    from sqlalchemy import select
    
    server_dao = ServerDAO(session)
    user_server_dao = UserServerDAO(session)
    
    # Получаем все активные серверы
    stmt = select(server_dao.model).where(
        server_dao.model.is_active == True,
        server_dao.model.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    servers = result.scalars().all()
    
    # Получаем серверы пользователя
    user_servers = await user_server_dao.find_by_user(user.id)
    user_server_ids = {us.server_id for us in user_servers}
    
    # Фильтруем только те, которые ещё не добавлены
    available_servers = [s for s in servers if s.id not in user_server_ids]
    
    return [
        ActiveServerResponse(
            id=s.id,
            name=s.name,
            url=s.url,
            speed=s.settings.get("speed", "x1") if s.settings else "x1"
        )
        for s in available_servers
    ]


@router.get("/user-servers/", response_model=List[UserServerWithDetails])
async def get_user_servers(
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> List[UserServerWithDetails]:
    """
    Получение списка серверов текущего пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)
    server_dao = ServerDAO(session)
    player_dao = PlayerDAO(session)
    
    # Получаем серверы пользователя
    user_servers = await user_server_dao.find_by_user(user.id)
    
    result = []
    for us in user_servers:
        # Получаем данные сервера
        server = await server_dao.find_one_or_none_by_id(us.server_id)
        if not server:
            continue
        
        # Получаем игрока
        player = await player_dao.find_by_user_and_server(user.id, us.server_id)
        
        result.append(UserServerWithDetails(
            id=us.id,
            server_id=us.server_id,
            server_name=server.name,
            server_url=server.url,
            server_speed=server.settings.get("speed", "x1") if server.settings else "x1",
            is_active=us.is_active,
            player_name=player.name if player else None,
            player_verified=player.is_verified if player else False
        ))
    
    return result


@router.post("/user-servers/", response_model=UserServerWithDetails)
async def add_user_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(get_current_user)
) -> UserServerWithDetails:
    """
    Добавить сервер в список пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)
    server_dao = ServerDAO(session)
    
    # Проверяем, что сервер существует и активен
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException("Сервер не найден")
    if not server.is_active:
        raise ForbiddenException("Сервер неактивен")
    
    # Добавляем сервер
    user_server = await user_server_dao.add_user_server(user.id, server_id)
    
    # Получаем игрока
    player_dao = PlayerDAO(session)
    player = await player_dao.find_by_user_and_server(user.id, server_id)
    
    return UserServerWithDetails(
        id=user_server.id,
        server_id=user_server.server_id,
        server_name=server.name,
        server_url=server.url,
        server_speed=server.settings.get("speed", "x1") if server.settings else "x1",
        is_active=user_server.is_active,
        player_name=player.name if player else None,
        player_verified=player.is_verified if player else False
    )


@router.post("/user-servers/{server_id}/select")
async def select_user_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(get_current_user)
) -> dict:
    """
    Выбрать сервер как активный для пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)
    
    # Проверяем, что сервер есть у пользователя
    user_servers = await user_server_dao.find_by_user(user.id)
    user_server_ids = {us.server_id for us in user_servers}
    
    if server_id not in user_server_ids:
        raise UserServerNotFoundException("Сервер не добавлен в ваш список")
    
    # Устанавливаем активный
    await user_server_dao.set_active(user.id, server_id)
    
    return {"message": "Сервер выбран"}


@router.post("/user-servers/{server_id}/deselect")
async def deselect_user_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(get_current_user)
) -> dict:
    """
    Снять активность с сервера для пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)

    # Проверяем, что сервер есть у пользователя
    user_servers = await user_server_dao.find_by_user(user.id)
    user_server_ids = {us.server_id for us in user_servers}

    if server_id not in user_server_ids:
        raise UserServerNotFoundException("Сервер не добавлен в ваш список")

    # Снимаем активность
    await user_server_dao.unset_active(user.id, server_id)

    return {"message": "Сервер откреплён"}


@router.delete("/user-servers/{server_id}")
async def remove_user_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user: User = Depends(get_current_user)
) -> dict:
    """
    Удалить сервер из списка пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)
    
    # Проверяем, что сервер есть у пользователя
    user_servers = await user_server_dao.find_by_user(user.id)
    user_server_ids = {us.server_id for us in user_servers}
    
    if server_id not in user_server_ids:
        raise UserServerNotFoundException("Сервер не добавлен в ваш список")
    
    # Удаляем
    await user_server_dao.remove_user_server(user.id, server_id)
    
    return {"message": "Сервер удалён из списка"}


# === Эндпоинты для обновления карты ===


@router.post("/servers/{server_id}/update-map", response_model=ServerUpdateResponse)
async def update_server_map(
    server_id: int,
    request: MapUpdateRequest = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_with_commit)
) -> ServerUpdateResponse:
    """
    Обновить карту для указанного сервера.
    Доступно для всех авторизованных пользователей.
    """
    # Используем scheduler для обновления
    result = await scheduler.update_server(server_id)
    
    # Получаем время последнего обновления
    last_update_info = None
    if result.get('status') == 'success':
        server_dao = ServerDAO(session)
        server = await server_dao.find_one_or_none_by_id(server_id)
        if server:
            last_update_info = server.last_update_info
    
    return ServerUpdateResponse(
        status=result.get('status', 'error'),
        server_id=server_id,
        server_name=result.get('server_name'),
        stats=result.get('stats'),
        error=result.get('error'),
        reason=result.get('reason'),
        last_update_info=last_update_info
    )


@router.post("/servers/update-all", response_model=UpdateAllResponse)
async def update_all_servers(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_with_commit)
) -> UpdateAllResponse:
    """
    Обновить карту для всех активных серверов.
    Доступно для всех авторизованных пользователей.
    """
    results = await scheduler.update_all_servers()
    
    response_results = []
    success = 0
    failed = 0
    skipped = 0


# === Эндпоинты для поиска клеток карты ===


@router.get("/api/servers/{server_id}/map-cells", response_model=MapCellSearchResponse)
async def search_map_cells(
    server_id: int,
    type_ids: str | None = None,
    min_crop: int = 0,
    min_wood: int = 0,
    min_clay: int = 0,
    min_iron: int = 0,
    occupied: str | None = None,
    page: int = 1,
    per_page: int = 20,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> MapCellSearchResponse:
    """
    Поиск клеток карты с фильтрами.
    Доступно для всех авторизованных пользователей.
    """
    # Проверяем, что сервер существует
    server_dao = ServerDAO(session)
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()

    # Преобразуем type_ids из строки в список
    type_ids_list = None
    if type_ids and type_ids.strip():
        try:
            type_ids_list = [int(x.strip()) for x in type_ids.split(',') if x.strip()]
        except ValueError:
            raise ForbiddenException("Некорректный формат type_ids")

    # Преобразуем occupied из строки в bool/None
    occupied_bool = None
    if occupied is not None and occupied != '' and occupied != 'null':
        occupied_bool = occupied.lower() == 'true'

    # Вызываем DAO
    map_dao = MapDAO(session)
    cells, total = await map_dao.search_cells(
        server_id=server_id,
        type_ids=type_ids_list,
        min_crop=min_crop,
        min_wood=min_wood,
        min_clay=min_clay,
        min_iron=min_iron,
        occupied=occupied_bool,
        page=page,
        per_page=per_page
    )

    pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return MapCellSearchResponse(
        cells=cells,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/api/servers/{server_id}/map-cells/{x}/{y}/area", response_model=MapAreaResponse)
async def get_map_area(
    server_id: int,
    x: int,
    y: int,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> MapAreaResponse:
    """
    Получить область карты 21x21 вокруг указанной клетки.
    Доступно для всех авторизованных пользователей.
    """
    # Проверяем, что сервер существует
    server_dao = ServerDAO(session)
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()

    # Валидируем координаты (диапазон для Travian карт)
    size = int(server.settings.get('Size', 400))
    if not (-size <= x <= size and -size <= y <= size):
        raise ForbiddenException("Некорректные координаты")

    # Вызываем DAO
    map_dao = MapDAO(session)
    cells = await map_dao.get_map_area(server_id, x, y)

    return MapAreaResponse(
        center_x=x,
        center_y=y,
        size=size,
        cells=cells
    )
    
    server_dao = ServerDAO(session)
    
    for server_id, result in results.items():
        status = result.get('status', 'error')
        
        # Получаем время последнего обновления
        last_update_info = None
        if status == 'success':
            server = await server_dao.find_one_or_none_by_id(server_id)
            if server:
                last_update_info = server.last_update_info
        
        response_results.append(ServerUpdateResponse(
            status=status,
            server_id=server_id,
            server_name=result.get('server_name'),
            stats=result.get('stats'),
            error=result.get('error'),
            reason=result.get('reason'),
            last_update_info=last_update_info
        ))
        
        if status == 'success':
            success += 1
        elif status == 'skipped':
            skipped += 1
        else:
            failed += 1
    
    return UpdateAllResponse(
        total=len(results),
        success=success,
        failed=failed,
        skipped=skipped,
        results=response_results
    )


@router.get("/servers/{server_id}/update-status", response_model=MapUpdateResponse)
async def get_server_update_status(
    server_id: int,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> MapUpdateResponse:
    """
    Получить статус последнего обновления карты для сервера.
    Доступно для всех авторизованных пользователей.
    """
    # Проверяем, что сервер существует
    server_dao = ServerDAO(session)
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    
    # Получаем статус обновления
    status = await map_update_service.get_last_update_status(server_id)
    
    if not status:
        return MapUpdateResponse(
            id=0,
            server_id=server_id,
            started_at=None,
            finished_at=None,
            status='never_updated',
            villages_processed=0,
            players_processed=0,
            alliances_processed=0,
            error_message=None,
            duration_ms=None
        )
    
    return MapUpdateResponse(**status)


# === Эндпоинты для просмотра данных ===

class AllianceListResponse(BaseModel):
    """Схема ответа со списком альянсов."""
    alliances: List[dict]
    total: int
    page: int
    per_page: int
    pages: int


class PlayerListResponse(BaseModel):
    """Схема ответа со списком игроков."""
    players: List[dict]
    total: int
    page: int
    per_page: int
    pages: int


class VillageListResponse(BaseModel):
    """Схема ответа со списком деревень."""
    villages: List[dict]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/api/servers/{server_id}/alliances", response_model=AllianceListResponse)
async def get_server_alliances(
    server_id: int,
    page: int = 1,
    per_page: int = 20,
    tag: str = None,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> AllianceListResponse:
    """
    Получить список альянсов сервера с пагинацией и фильтрацией.
    """
    # Проверяем, что сервер существует
    server_dao = ServerDAO(session)
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    
    from sqlalchemy import select, func
    from app.game.models import Alliance
    
    # Базовый запрос
    query = select(Alliance).where(Alliance.server_id == server_id)
    count_query = select(func.count()).where(Alliance.server_id == server_id)
    
    # Фильтр по тегу
    if tag:
        query = query.where(Alliance.tag.ilike(f"%{tag}%"))
        count_query = count_query.where(Alliance.tag.ilike(f"%{tag}%"))
    
    # Пагинация
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Выполнение запросов
    result = await session.execute(query)
    alliances = result.scalars().all()
    
    count_result = await session.execute(count_query)
    total = count_result.scalar()
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return AllianceListResponse(
        alliances=[{
            'id': a.id,
            'alliance_id': a.alliance_id,
            'tag': a.tag,
            'name': a.name,
            'players_count': a.players_count,
            'population': a.population,
            'last_seen_at': a.last_seen_at.isoformat() if a.last_seen_at else None
        } for a in alliances],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/api/servers/{server_id}/players", response_model=PlayerListResponse)
async def get_server_players(
    server_id: int,
    page: int = 1,
    per_page: int = 20,
    name: str = None,
    alliance: str = None,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> PlayerListResponse:
    """
    Получить список игроков сервера с пагинацией и фильтрацией.
    """
    # Проверяем, что сервер существует
    server_dao = ServerDAO(session)
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    
    from sqlalchemy import select, func
    from app.game.models import Player, Alliance
    
    # Базовый запрос с join для фильтрации по альянсу
    query = select(Player).where(Player.server_id == server_id)
    count_query = select(func.count()).where(Player.server_id == server_id)
    
    # Фильтр по имени
    if name:
        query = query.where(Player.name.ilike(f"%{name}%"))
        count_query = count_query.where(Player.name.ilike(f"%{name}%"))
    
    # Пагинация
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Выполнение запросов
    result = await session.execute(query)
    players = result.scalars().all()
    
    count_result = await session.execute(count_query)
    total = count_result.scalar()
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    # Получаем теги альянсов
    player_data = []
    for p in players:
        alliance_tag = None
        if p.alliance_id:
            alliance_result = await session.execute(
                select(Alliance).where(Alliance.id == p.alliance_id)
            )
            alliance_obj = alliance_result.scalar_one_or_none()
            alliance_tag = alliance_obj.tag if alliance_obj else None
        
        player_data.append({
            'id': p.id,
            'name': p.name,
            'alliance_tag': alliance_tag,
            'villages_count': p.villages_count,
            'population': p.population,
            'race_id': p.race_id,
            'last_seen_at': p.last_seen_at.isoformat() if p.last_seen_at else None
        })
    
    return PlayerListResponse(
        players=player_data,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/api/servers/{server_id}/villages", response_model=VillageListResponse)
async def get_server_villages(
    server_id: int,
    page: int = 1,
    per_page: int = 20,
    name: str = None,
    player: str = None,
    session: AsyncSession = Depends(get_session_without_commit),
    user: User = Depends(get_current_user)
) -> VillageListResponse:
    """
    Получить список деревень сервера с пагинацией и фильтрацией.
    """
    # Проверяем, что сервер существует
    server_dao = ServerDAO(session)
    server = await server_dao.find_one_or_none_by_id(server_id)
    if not server:
        raise ServerNotFoundException()
    
    from sqlalchemy import select, func
    from app.game.models import Village, Player
    
    # Базовый запрос
    query = select(Village).where(Village.server_id == server_id)
    count_query = select(func.count()).where(Village.server_id == server_id)
    
    # Фильтр по названию
    if name:
        query = query.where(Village.name.ilike(f"%{name}%"))
        count_query = count_query.where(Village.name.ilike(f"%{name}%"))
    
    # Пагинация
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Выполнение запросов
    result = await session.execute(query)
    villages = result.scalars().all()
    
    count_result = await session.execute(count_query)
    total = count_result.scalar()
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    # Получаем имена игроков
    village_data = []
    for v in villages:
        player_name = None
        if v.player_id:
            player_result = await session.execute(
                select(Player).where(Player.id == v.player_id)
            )
            player_obj = player_result.scalar_one_or_none()
            player_name = player_obj.name if player_obj else None
        
        village_data.append({
            'id': v.id,
            'name': v.name,
            'player_name': player_name,
            'x': v.x,
            'y': v.y,
            'village_type': v.village_type,
            'population': v.population,
            'last_seen_at': v.last_seen_at.isoformat() if v.last_seen_at else None
        })
    
    return VillageListResponse(
        villages=village_data,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )

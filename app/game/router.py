from typing import List, Dict, Any, Optional
from loguru import logger
from fastapi import APIRouter, Depends, Header, Request, HTTPException
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.auth.models import User
from app.dependencies.auth_dep import get_current_user
from app.dependencies.dao_dep import get_session_with_commit, get_session_without_commit
from app.game.dao import ServerDAO, UserServerDAO, PlayerDAO, MapDAO, ApiKeyDAO
from app.game.models import Server
from app.game.schemas import (
    ServerCreate, ServerUpdate, ServerResponse, UserServerResponse,
    MapUpdateResponse, MapUpdateRequest, ServerUpdateResponse, UpdateAllResponse,
    MapCellFilterRequest, MapCellSearchResponse, MapAreaResponse,
    PlayerVerificationStatusResponse, PlayerSelectRequest, PlayerVerificationUpdate
)
from app.exceptions import UserNotFoundException, ServerAlreadyExistsException, ForbiddenException, ServerUrlAlreadyExistsException, ServerNotFoundException, UserServerNotFoundException
from app.services.scheduler import scheduler
from app.services.map_update import map_update_service
from app.presentation.dependencies.permissions import require_permission, get_user_context
from app.domain.permissions import Permission, UserContext
from app.utils.code_generator import decode_player_name


def normalize_server_url(url: str) -> list[str]:
    """
    Нормализует URL сервера для поиска в БД.
    Возвращает список вариантов URL для поиска.
    
    Пример: ts8.x1.europe.travian.com ->
        ['ts8.x1.europe.travian.com', 'https://ts8.x1.europe.travian.com', 'https://ts8.x1.europe.travian.com/']
    """
    variants = []
    
    # Убираем протокол и trailing slash для получения "чистого" хоста
    clean = url
    if clean.startswith("https://"):
        clean = clean[8:]
    elif clean.startswith("http://"):
        clean = clean[7:]
    clean = clean.rstrip("/")
    
    # Формируем варианты
    variants.append(clean)                              # ts8.x1.europe.travian.com
    variants.append(f"https://{clean}")                 # https://ts8.x1.europe.travian.com
    variants.append(f"https://{clean}/")                # https://ts8.x1.europe.travian.com/
    variants.append(f"http://{clean}")                  # http://ts8.x1.europe.travian.com
    variants.append(f"http://{clean}/")                 # http://ts8.x1.europe.travian.com/
    
    return variants


async def verify_api_key(
    x_auth_key: str = Header(..., alias="X-Auth-Key"),
    x_server: str = Header(..., alias="X-Server"),
    x_player_name: str = Header(..., alias="X-Player-Name"),
    session: AsyncSession = Depends(get_session_without_commit)
):
    """
    Dependency для проверки API-ключа.
    Возвращает информацию об игроке и сервере или выбрасывает 401.
    """
    player_name = decode_player_name(x_player_name)
    
    logger.info(f"[verify_api_key] x_auth_key: {x_auth_key}")
    logger.info(f"[verify_api_key] x_server: {x_server}")
    logger.info(f"[verify_api_key] x_player_name (raw): {x_player_name}")
    logger.info(f"[verify_api_key] player_name (decoded): {player_name}")
    
    # Нормализуем URL и ищем сервер по всем вариантам
    url_variants = normalize_server_url(x_server)
    logger.info(f"[verify_api_key] URL variants for search: {url_variants}")
    
    server_dao = ServerDAO(session)
    stmt = select(server_dao.model).where(server_dao.model.url.in_(url_variants))
    result = await session.execute(stmt)
    server = result.scalar_one_or_none()
    
    logger.info(f"[verify_api_key] server found: {server.id if server else 'None'} (url={server.url if server else 'N/A'})")
    
    if not server:
        logger.warning(f"[verify_api_key] Server not found for URL: {x_server} (variants: {url_variants})")
        raise HTTPException(status_code=401, detail="Server not found")
    
    # Находим игрока
    player_dao = PlayerDAO(session)
    stmt = select(player_dao.model).where(
        player_dao.model.server_id == server.id,
        player_dao.model.name == player_name
    )
    result = await session.execute(stmt)
    player = result.scalar_one_or_none()
    
    logger.info(f"[verify_api_key] player found: {player.id if player else 'None'} (name={player_name}, server_id={server.id})")
    
    if not player:
        logger.warning(f"[verify_api_key] Player not found: name={player_name}, server_id={server.id}")
        raise HTTPException(status_code=401, detail="Player not found")
    
    # Проверяем API-ключ
    api_key_dao = ApiKeyDAO(session)
    api_key = await api_key_dao.find_by_player_and_server(
        player.id, server.id, only_active=True
    )
    
    logger.info(f"[verify_api_key] x_auth_key: {x_auth_key} | player_name: {player_name} | server_url: {server.url}")
    logger.info(f"[verify_api_key] api_key from DB: {api_key.key_value if api_key else 'None'}")
    logger.info(f"[verify_api_key] api_key is_active: {api_key.is_active if api_key else 'N/A'}")
    
    if not api_key or api_key.key_value != x_auth_key:
        logger.warning(f"[verify_api_key] Invalid or expired auth key. DB key: {api_key.key_value if api_key else 'None'}, received: {x_auth_key}")
        raise HTTPException(status_code=401, detail="Invalid or expired auth key")
    
    # Проверяем, что игрок всё ещё привязан к пользователю
    if not player.user_id:
        raise HTTPException(status_code=401, detail="Player not linked to any account")
    
    # Возвращаем информацию для дальнейшего использования
    return {
        "player": player,
        "server": server,
        "player_name": player_name,
        "player_id": player.id,
        "server_id": server.id
    }


router = APIRouter()


class ServerListResponse(BaseModel):
    """Схема ответа со списком серверов."""
    servers: List[ServerResponse]
    total: int
    page: int
    per_page: int
    pages: int


# Эндпоинты для управления серверами

@router.get("/servers/", response_model=ServerListResponse)
async def get_servers(
    page: int = 1,
    per_page: int = 10,
    name: str | None = None,
    is_active: str | None = None,
    is_deleted: str | None = None,
    session: AsyncSession = Depends(get_session_without_commit),
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_MANAGE))
) -> ServerListResponse:
    """
    Получение списка серверов с пагинацией и фильтрацией.
    Доступно для Админа (id=4) и Модератора (id=2).
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
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_MANAGE))
) -> ServerResponse:
    """
    Создание нового сервера.
    Доступно для Админа (id=4) и Модератора (id=2).
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
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_MANAGE))
) -> ServerResponse:
    """
    Получение сервера по ID.
    Доступно для Админа (id=4) и Модератора (id=2).
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
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_MANAGE))
) -> ServerResponse:
    """
    Обновление сервера.
    Доступно для Админа (id=4) и Модератора (id=2).
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
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_DELETE))
) -> dict:
    """
    Мягкое удаление сервера.
    Доступно для Админа (id=4) и Модератора (id=2).
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
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_MANAGE))
) -> dict:
    """
    Восстановление удалённого сервера.
    Доступно для Админа (id=4) и Модератора (id=2).
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
    player_id: int | None = None
    verification_code: str | None = None


class ActiveServerResponse(BaseModel):
    """Схема активного сервера для добавления."""
    id: int
    name: str
    url: str
    speed: str


@router.get("/servers/active/", response_model=List[ActiveServerResponse])
async def get_active_servers(
    session: AsyncSession = Depends(get_session_without_commit),
    user_context: UserContext = Depends(get_user_context)
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
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
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
    user_context: UserContext = Depends(get_user_context)
) -> List[UserServerWithDetails]:
    """
    Получение списка серверов текущего пользователя.
    Доступно для всех авторизованных пользователей.
    """
    from app.game.dao import PlayerVerificationDAO
    
    user_server_dao = UserServerDAO(session)
    server_dao = ServerDAO(session)
    player_dao = PlayerDAO(session)
    verification_dao = PlayerVerificationDAO(session)
    
    # Получаем серверы пользователя
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
    
    result = []
    for us in user_servers:
        # Получаем данные сервера
        server = await server_dao.find_one_or_none_by_id(us.server_id)
        if not server:
            continue
        
        # Получаем игрока
        player = await player_dao.find_by_user_and_server(user_context.user_id, us.server_id)
        
        # Получаем код подтверждения если есть
        verification_code = None
        player_id = None
        if player:
            player_id = player.id
            verification = await verification_dao.find_by_user_and_player(
                user_context.user_id, player.id, us.server_id
            )
            if verification and not verification.is_verified:
                verification_code = verification.verification_code
        
        result.append(UserServerWithDetails(
            id=us.id,
            server_id=us.server_id,
            server_name=server.name,
            server_url=server.url,
            server_speed=server.settings.get("speed", "x1") if server.settings else "x1",
            is_active=us.is_active,
            player_name=player.name if player else None,
            player_verified=player.is_verified if player else False,
            player_id=player_id,
            verification_code=verification_code
        ))
    
    return result


@router.post("/user-servers/", response_model=UserServerWithDetails)
async def add_user_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user_context: UserContext = Depends(get_user_context)
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
    user_server = await user_server_dao.add_user_server(user_context.user_id, server_id)
    
    # Получаем игрока
    player_dao = PlayerDAO(session)
    player = await player_dao.find_by_user_and_server(user_context.user_id, server_id)
    
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
    user_context: UserContext = Depends(get_user_context)
) -> dict:
    """
    Выбрать сервер как активный для пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)
    
    # Проверяем, что сервер есть у пользователя
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
    user_server_ids = {us.server_id for us in user_servers}
    
    if server_id not in user_server_ids:
        raise UserServerNotFoundException("Сервер не добавлен в ваш список")
    
    # Устанавливаем активный
    await user_server_dao.set_active(user_context.user_id, server_id)
    
    return {"message": "Сервер выбран"}


@router.post("/user-servers/{server_id}/deselect")
async def deselect_user_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user_context: UserContext = Depends(get_user_context)
) -> dict:
    """
    Снять активность с сервера для пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)

    # Проверяем, что сервер есть у пользователя
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
    user_server_ids = {us.server_id for us in user_servers}

    if server_id not in user_server_ids:
        raise UserServerNotFoundException("Сервер не добавлен в ваш список")

    # Снимаем активность
    await user_server_dao.unset_active(user_context.user_id, server_id)

    return {"message": "Сервер откреплён"}


@router.delete("/user-servers/{server_id}")
async def remove_user_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user_context: UserContext = Depends(get_user_context)
) -> dict:
    """
    Удалить сервер из списка пользователя.
    Доступно для всех авторизованных пользователей.
    """
    user_server_dao = UserServerDAO(session)
    
    # Проверяем, что сервер есть у пользователя
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
    user_server_ids = {us.server_id for us in user_servers}
    
    if server_id not in user_server_ids:
        raise UserServerNotFoundException("Сервер не добавлен в ваш список")
    
    # Удаляем
    await user_server_dao.remove_user_server(user_context.user_id, server_id)
    
    return {"message": "Сервер удалён"}


# === Эндпоинты для работы с игроками и подтверждением ===

class PlayerAttachRequest(BaseModel):
    """Схема запроса привязки игрока."""
    player_name: str = Field(..., min_length=1, max_length=255, description="Имя игрока")


class PlayerDetachResponse(BaseModel):
    """Схема ответа отвязки игрока."""
    success: bool
    message: str


class BrowserVerificationRequest(BaseModel):
    """Схема запроса от расширения браузера."""
    verification_code: str = Field(..., min_length=4, max_length=10, description="Код подтверждения")
    player_account_id: int = Field(..., description="ID игрока из игры (account_id)")
    server_url: str = Field(..., description="URL сервера")


class BrowserVerificationResponse(BaseModel):
    """Схема ответа для расширения браузера."""
    success: bool
    message: str
    player_verified: bool = False
    api_key: str | None = None
    is_verified: bool = False


@router.post("/servers/{server_id}/players/attach")
async def attach_player_by_name(
    server_id: int,
    request: PlayerAttachRequest,
    session: AsyncSession = Depends(get_session_with_commit),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Привязать игрока по имени и получить код подтверждения.
    """
    from app.game.dao import UserServerDAO, PlayerDAO, PlayerVerificationDAO
    from app.utils.code_generator import generate_verification_code
    from sqlalchemy import select
    
    # Проверяем, что сервер есть у пользователя
    user_server_dao = UserServerDAO(session)
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
    if server_id not in [us.server_id for us in user_servers]:
        raise ForbiddenException("Сервер не добавлен в ваш список")
    
    # Ищем игрока по имени на сервере
    player_dao = PlayerDAO(session)
    stmt = select(player_dao.model).where(
        player_dao.model.server_id == server_id,
        player_dao.model.name == request.player_name
    )
    result = await session.execute(stmt)
    player = result.scalar_one_or_none()
    
    if not player:
        return {
            "status": "not_found",
            "message": f"Игрок '{request.player_name}' не найден на этом сервере"
        }
    
    # Проверяем, не привязан ли уже этот игрок к другому пользователю
    if player.user_id and player.user_id != user_context.user_id:
        raise ForbiddenException("Этот игрок уже привязан к другому аккаунту")
    
    # Если игрок уже привязан к этому пользователю
    if player.user_id == user_context.user_id:
        verification_dao = PlayerVerificationDAO(session)
        verification = await verification_dao.find_by_user_and_player(
            user_context.user_id, player.id, server_id
        )
        
        if verification and verification.is_verified:
            return {
                "status": "already_verified",
                "player_id": player.id,
                "player_name": player.name,
                "player_account_id": player.account_id,
                "is_verified": True,
                "message": "Игрок уже подтверждён"
            }
        elif verification:
            return {
                "status": "pending",
                "player_id": player.id,
                "player_name": player.name,
                "player_account_id": player.account_id,
                "verification_code": verification.verification_code,
                "is_verified": False,
                "message": "Ожидает подтверждения"
            }
    
    # Привязываем игрока к пользователю
    player.user_id = user_context.user_id
    await session.flush()
    
    # Генерируем код подтверждения
    verification_code = generate_verification_code()
    
    # Создаём или обновляем запись подтверждения
    verification_dao = PlayerVerificationDAO(session)
    verification = await verification_dao.create_or_update(
        user_id=user_context.user_id,
        player_id=player.id,
        server_id=server_id,
        verification_code=verification_code
    )
    
    return {
        "status": "success",
        "player_id": player.id,
        "player_name": player.name,
        "player_account_id": player.account_id,
        "verification_code": verification.verification_code,
        "is_verified": False,
        "message": "Код подтверждения сгенерирован"
    }


@router.post("/servers/{server_id}/players/detach")
async def detach_player(
    server_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    user_context: UserContext = Depends(get_user_context)
) -> PlayerDetachResponse:
    """
    Отвязать игрока от пользователя.
    """
    from app.game.dao import UserServerDAO, PlayerDAO, PlayerVerificationDAO
    
    # Проверяем, что сервер есть у пользователя
    user_server_dao = UserServerDAO(session)
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
    if server_id not in [us.server_id for us in user_servers]:
        raise ForbiddenException("Сервер не добавлен в ваш список")
    
    # Находим игрока
    player_dao = PlayerDAO(session)
    player = await player_dao.find_by_user_and_server(user_context.user_id, server_id)
    
    if not player:
        raise ForbiddenException("Игрок не привязан")
    
    # Удаляем подтверждение
    verification_dao = PlayerVerificationDAO(session)
    verification = await verification_dao.find_by_user_and_player(
        user_context.user_id, player.id, server_id
    )
    if verification:
        await verification_dao.delete_by_id(verification.id)

    api_key_dao = ApiKeyDAO(session)
    await api_key_dao.deactivate_all_for_player(player.id, server_id)
    
    # Сбрасываем связь
    player.user_id = None
    player.is_verified = False
    await session.flush()
    
    return PlayerDetachResponse(
        success=True,
        message="Игрок отвязан"
    )


@router.get("/servers/{server_id}/players/status")
async def get_player_verification_status(
    server_id: int,
    session: AsyncSession = Depends(get_session_without_commit),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Получить статус подтверждения привязанного игрока.
    """
    from app.game.dao import UserServerDAO, PlayerDAO, PlayerVerificationDAO
    
    # Проверяем, что сервер есть у пользователя
    user_server_dao = UserServerDAO(session)
    user_servers = await user_server_dao.find_by_user(user_context.user_id)
    if server_id not in [us.server_id for us in user_servers]:
        raise ForbiddenException("Сервер не добавлен в ваш список")
    
    # Находим игрока
    player_dao = PlayerDAO(session)
    player = await player_dao.find_by_user_and_server(user_context.user_id, server_id)
    
    if not player:
        return {
            "has_player": False,
            "message": "Игрок не привязан"
        }
    
    # Получаем статус подтверждения
    verification_dao = PlayerVerificationDAO(session)
    verification = await verification_dao.find_by_user_and_player(
        user_context.user_id, player.id, server_id
    )
    
    return {
        "has_player": True,
        "player_id": player.id,
        "player_name": player.name,
        "player_account_id": player.account_id,
        "is_verified": verification.is_verified if verification else player.is_verified,
        "verification_code": verification.verification_code if verification and not verification.is_verified else None,
        "verified_at": verification.verified_at if verification else None
    }


@router.post("/browser/verify", response_model=BrowserVerificationResponse)
async def browser_verify_player(
    request: BrowserVerificationRequest,
    session: AsyncSession = Depends(get_session_with_commit)
):
    """
    Эндпоинт для расширения браузера.
    Подтверждает игрока по коду и возвращает API-ключ.
    """
    from app.game.dao import ServerDAO, PlayerDAO, PlayerVerificationDAO, ApiKeyDAO
    from sqlalchemy import select
    import secrets
    
    # Находим сервер по URL (с нормализацией)
    url_variants = normalize_server_url(request.server_url)
    server_dao = ServerDAO(session)
    stmt = select(server_dao.model).where(server_dao.model.url.in_(url_variants))
    result = await session.execute(stmt)
    server = result.scalar_one_or_none()
    
    if not server:
        return BrowserVerificationResponse(
            success=False,
            message="Сервер не найден",
            player_verified=False,
            api_key=None
        )
    
    # Находим игрока по server_id и account_id
    player_dao = PlayerDAO(session)
    stmt = select(player_dao.model).where(
        player_dao.model.server_id == server.id,
        player_dao.model.account_id == request.player_account_id
    )
    result = await session.execute(stmt)
    player = result.scalar_one_or_none()
    
    if not player:
        return BrowserVerificationResponse(
            success=False,
            message=f"Игрок с ID {request.player_account_id} не найден на сервере {server.name}",
            player_verified=False,
            api_key=None
        )
    
    # Проверяем, что игрок привязан к какому-то пользователю
    if not player.user_id:
        return BrowserVerificationResponse(
            success=False,
            message="Этот игрок не привязан ни к одному аккаунту. Сначала привяжите игрока в панели управления.",
            player_verified=False,
            api_key=None
        )
    
    # Ищем запись подтверждения
    verification_dao = PlayerVerificationDAO(session)
    verification = await verification_dao.find_by_user_and_player(
        user_id=player.user_id,
        player_id=player.id,
        server_id=server.id
    )
    
    if not verification:
        return BrowserVerificationResponse(
            success=False,
            message="Запрос на подтверждение не найден. Сначала привяжите игрока в панели управления.",
            player_verified=False,
            api_key=None
        )
    
    if verification.is_verified:
        # Уже подтверждён — возвращаем существующий ключ
        api_key_dao = ApiKeyDAO(session)
        existing_key = await api_key_dao.find_by_player_and_server(
            player.id, server.id, only_active=True
        )
        
        if existing_key:
            return BrowserVerificationResponse(
                success=True,
                message="Игрок уже подтверждён",
                player_verified=True,
                api_key=existing_key.key_value,
                is_verified=True
            )
        else:
            # Если ключа нет — генерируем новый
            new_key = secrets.token_urlsafe(32)
            new_api_key = await api_key_dao.create_key(player.id, server.id, new_key)
            return BrowserVerificationResponse(
                success=True,
                message="Игрок уже подтверждён, ключ восстановлен",
                player_verified=True,
                api_key=new_api_key.key_value,
                is_verified=True
            )
    
    # Проверяем код
    if verification.verification_code != request.verification_code:
        return BrowserVerificationResponse(
            success=False,
            message="Неверный код подтверждения",
            player_verified=False,
            api_key=None
        )
    
    # Подтверждаем игрока
    success = await verification_dao.verify(
        user_id=player.user_id,
        player_id=player.id,
        server_id=server.id,
        code=request.verification_code
    )
    
    if not success:
        return BrowserVerificationResponse(
            success=False,
            message="Ошибка при подтверждении",
            player_verified=False,
            api_key=None
        )
    
    # Генерируем API-ключ для расширения
    new_key = secrets.token_urlsafe(32)
    api_key_dao = ApiKeyDAO(session)
    new_api_key = await api_key_dao.create_key(player.id, server.id, new_key)
    
    print(f"[DEBUG] Returning response: success={success}, has_api_key={bool(new_api_key)}")

    return BrowserVerificationResponse(
        success=True,
        message="Игрок успешно подтверждён! API-ключ сгенерирован.",
        player_verified=True,
        api_key=new_api_key.key_value,
        is_verified=True
    )


# === Эндпоинты для обновления карты ===


@router.post("/servers/{server_id}/update-map", response_model=ServerUpdateResponse)
async def update_server_map(
    server_id: int,
    request: MapUpdateRequest = None,
    user_context: UserContext = Depends(get_user_context),
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
    user_context: UserContext = Depends(get_user_context),
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
    user_context: UserContext = Depends(get_user_context)
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
    user_context: UserContext = Depends(get_user_context)
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


@router.get("/servers/{server_id}/update-status", response_model=MapUpdateResponse)
async def get_server_update_status(
    server_id: int,
    session: AsyncSession = Depends(get_session_without_commit),
    user_context: UserContext = Depends(get_user_context)
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
    user_context: UserContext = Depends(get_user_context)
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
    user_context: UserContext = Depends(get_user_context)
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
    user_context: UserContext = Depends(get_user_context)
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


# === Эндпоинты для работы с API ключами ===


class AuthKeyRequest(BaseModel):
    """Схема запроса ключа авторизации."""
    server: str = Field(..., description="URL сервера")
    player_name: str = Field(..., description="Имя игрока")
    request_time: str = Field(..., description="Время запроса")


@router.post("/api/auth/key")
async def get_auth_key(
    request: AuthKeyRequest,
    session: AsyncSession = Depends(get_session_without_commit)
):
    """
    Получить API-ключ для расширения.
    Эндпоинт публичный, не требует авторизации.
    """
    from app.game.dao import ServerDAO, PlayerDAO, ApiKeyDAO
    from sqlalchemy import select
    import secrets
    
    # Находим сервер по URL (с нормализацией)
    url_variants = normalize_server_url(request.server)
    server_dao = ServerDAO(session)
    stmt = select(server_dao.model).where(server_dao.model.url.in_(url_variants))
    result = await session.execute(stmt)
    server = result.scalar_one_or_none()
    
    if not server:
        return {
            "status": "denied",
            "key": None,
            "message": "Сервер не найден"
        }
    
    # Находим игрока
    player_dao = PlayerDAO(session)
    stmt = select(player_dao.model).where(
        player_dao.model.server_id == server.id,
        player_dao.model.name == request.player_name
    )
    result = await session.execute(stmt)
    player = result.scalar_one_or_none()
    
    if not player:
        return {
            "status": "denied",
            "key": None,
            "message": "Игрок не найден"
        }
    
    # Проверяем, что игрок подтверждён
    if not player.is_verified:
        return {
            "status": "pending",
            "key": None,
            "message": "Игрок не подтверждён. Сначала введите код подтверждения."
        }
    
    # Проверяем, что игрок привязан к пользователю
    if not player.user_id:
        return {
            "status": "pending",
            "key": None,
            "message": "Игрок не привязан к аккаунту"
        }
    
    # Ищем активный API-ключ
    api_key_dao = ApiKeyDAO(session)
    api_key = await api_key_dao.find_by_player_and_server(
        player.id, server.id, only_active=True
    )
    
    if api_key:
        return {
            "status": "confirmed",
            "key": api_key.key_value,
            "message": "Ключ получен"
        }
    
    # Если ключа нет — генерируем новый (только если игрок подтверждён и привязан)
    new_key = secrets.token_urlsafe(32)
    
    # Для создания ключа нужна сессия с коммитом, создаём новую
    from app.dao.database import async_session_maker
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async with AsyncSession(async_session_maker()) as write_session:
        write_api_key_dao = ApiKeyDAO(write_session)
        new_api_key = await write_api_key_dao.create_key(player.id, server.id, new_key)
        await write_session.commit()
        
        return {
            "status": "confirmed",
            "key": new_api_key.key_value,
            "message": "Ключ сгенерирован"
        }


@router.get("/servers/status")
async def get_server_player_status(
    player_name: str,
    server_url: str,
    session: AsyncSession = Depends(get_session_without_commit)
    # Убираем user_context — делаем публичным
):
    """
    Получить статус подтверждения игрока.
    Публичный эндпоинт, не требует авторизации.
    """
    from app.game.dao import ServerDAO, PlayerDAO
    from sqlalchemy import select
    
    logger.info(f"[servers/status] called: player_name={player_name}, server_url={server_url}")
    
    # Нормализуем URL и ищем сервер по всем вариантам
    url_variants = normalize_server_url(server_url)
    logger.info(f"[servers/status] URL variants: {url_variants}")
    
    server_dao = ServerDAO(session)
    stmt = select(server_dao.model).where(server_dao.model.url.in_(url_variants))
    result = await session.execute(stmt)
    server = result.scalar_one_or_none()
    
    if not server:
        logger.warning(f"[servers/status] Server not found: {server_url} (variants: {url_variants})")
        return {
            "is_verified": False,
            "message": "Сервер не найден"
        }
    
    # Находим игрока по имени и серверу
    player_dao = PlayerDAO(session)
    stmt = select(player_dao.model).where(
        player_dao.model.server_id == server.id,
        player_dao.model.name == player_name
    )
    result = await session.execute(stmt)
    player = result.scalar_one_or_none()
    
    if not player:
        print(f"[DEBUG] Player not found: {player_name} on server {server.id}")
        return {
            "is_verified": False,
            "message": "Игрок не найден"
        }
    
    print(f"[DEBUG] Player found: id={player.id}, is_verified={player.is_verified}, user_id={player.user_id}")
    
    # Возвращаем статус (не проверяем привязку к пользователю)
    return {
        "is_verified": player.is_verified,
        "player_id": player.id,
        "player_name": player.name,
        "player_account_id": player.account_id,
        "has_user": player.user_id is not None,
        "message": "Подтверждён" if player.is_verified else "Не подтверждён"
    }


# === Эндпоинты для приёма данных от расширения ===

class AttackDataRequest(BaseModel):
    """Схема запроса данных об атаках."""
    message_id: str = Field(..., description="ID сообщения")
    type: str = Field(..., description="Тип данных: village/alliance")
    data: List[Dict[str, Any]] = Field(..., description="Данные атак")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные")


class RallyPointRequest(BaseModel):
    """Схема запроса данных из пункта сбора."""
    message_id: str = Field(..., description="ID сообщения")
    type: str = Field("rally_point", description="Тип данных")
    movement_info: List[Dict[str, Any]] = Field(..., description="Информация о перемещениях")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные")


@router.post("/api/attacks")
async def receive_attack_data(
    request: Request,
    data: Dict[str, Any],
    auth_info: dict = Depends(verify_api_key)
):
    """
    Эндпоинт для приёма данных об атаках от расширения.
    Сохраняет данные в лог-файл.
    """
    from app.services.attack_logger import attack_logger
    
    player_name = auth_info["player_name"]
    server = auth_info["server"]
    
    logger.info(f"Received attack data from {player_name} on {server.url} (key verified)")
    
    # Получаем тело запроса
    body_bytes = await request.body()
    raw_body = body_bytes.decode('utf-8') if body_bytes else ""
    
    # Логируем данные
    attack_logger.log_attack_data(data, dict(request.headers), raw_body)
    
    return {
        "status": "success",
        "message": "Attack data received and saved",
        "message_id": data.get("message_id"),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/api/rally-point")
async def receive_rally_point_data(
    request: Request,
    data: Dict[str, Any],
    auth_info: dict = Depends(verify_api_key)
):
    """
    Эндпоинт для приёма данных из пункта сбора от расширения.
    Сохраняет данные в лог-файл.
    """
    from app.services.attack_logger import rally_point_logger
    
    player_name = auth_info["player_name"]
    server = auth_info["server"]
    
    logger.info(f"Received rally point data from {player_name} on {server.url} (key verified)")
    
    # Получаем тело запроса
    body_bytes = await request.body()
    raw_body = body_bytes.decode('utf-8') if body_bytes else ""
    
    # Логируем данные
    rally_point_logger.log_rally_data(data, dict(request.headers), raw_body)
    
    return {
        "status": "success",
        "message": "Rally point data received and saved",
        "message_id": data.get("message_id"),
        "movements_count": len(data.get("movement_info", [])),
        "timestamp": datetime.now().isoformat()
    }


# === Эндпоинты для приёма данных от расширения ===

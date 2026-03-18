from typing import List
from fastapi import APIRouter, Response, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.limiter import limiter
from app.auth.utils import authenticate_user, set_tokens, get_password_hash
from app.dependencies.auth_dep import get_current_user, get_current_admin_user, check_refresh_token, get_current_superadmin_user
from app.dependencies.dao_dep import get_session_with_commit, get_session_without_commit
from app.exceptions import UserAlreadyExistsException, IncorrectEmailOrPasswordException, UserNotFoundException
from app.auth.dao import UsersDAO, RegistrationTokensDAO
from app.game.dao import UserServerDAO, ServerDAO, PlayerDAO
from app.auth.schemas import (
    SUserRegister, SUserAuth, UsernameModel, EmailModel, SUserAddDB, SUserInfo,
    SUserUpdate, SUserCreate, SPasswordReset, SUserListResponse,
    SRegistrationTokenCreate, SRegistrationToken, SRegistrationTokenUpdate, SRegistrationTokenListResponse,
    SGenerateKeysRequest
)

router = APIRouter()


async def _user_to_suserinfo(user: User, session: AsyncSession | None = None) -> SUserInfo:
    """Конвертирует объект User в SUserInfo с данными о выбранном сервере."""
    # Используем role_id напрямую, избегая lazy loading
    role_id = user.role_id if user.role_id else 1
    
    # Если есть сессия, получаем название роли
    if session:
        from app.auth.dao import RoleDAO
        role_dao = RoleDAO(session)
        role = await role_dao.find_role_by_id(role_id)
        role_name = role.name if role else "User"
    else:
        role_name = "User"
    
    # Получаем выбранный сервер и игрока
    selected_server_id = None
    selected_server_name = None
    player_name = None
    
    if session:
        try:
            from app.game.dao import UserServerDAO, ServerDAO, PlayerDAO
            user_server_dao = UserServerDAO(session)
            active_server = await user_server_dao.find_active(user.id)
            
            if active_server:
                selected_server_id = active_server.server_id
                server_dao = ServerDAO(session)
                server = await server_dao.find_one_or_none_by_id(active_server.server_id)
                if server:
                    selected_server_name = server.name
                    
                    # Получаем игрока
                    player_dao = PlayerDAO(session)
                    player = await player_dao.find_by_user_and_server(user.id, active_server.server_id)
                    if player:
                        player_name = player.name
        except Exception:
            pass  # Игнорируем ошибки, возвращаем базовую информацию
    
    return SUserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        role_id=role_id,
        role_name=role_name,
        is_active=user.is_active,
        info=user.info,
        deleted_at=user.deleted_at,
        selected_server_id=selected_server_id,
        selected_server_name=selected_server_name,
        player_name=player_name
    )


@router.post("/register/")
async def register_user(user_data: SUserRegister,
                        session: AsyncSession = Depends(get_session_with_commit)) -> dict:
    # Проверка существования пользователя по username
    user_dao = UsersDAO(session)

    existing_user = await user_dao.find_one_or_none(filters=UsernameModel(username=user_data.username))
    if existing_user:
        raise UserAlreadyExistsException
    
    # Проверка существования пользователя по email
    existing_email = await user_dao.find_one_or_none(filters=EmailModel(email=user_data.email))
    if existing_email:
        raise UserAlreadyExistsException

    # Проверка токена
    tokens_dao = RegistrationTokensDAO(session)
    token = await tokens_dao.get_valid_token(user_data.token)
    if not token:
        raise HTTPException(status_code=400, detail="Неверный или использованный токен")

    # Подготовка данных для добавления
    user_data_dict = user_data.model_dump()
    user_data_dict.pop('confirm_password', None)
    user_data_dict.pop('token', None)
    
    # Хешируем пароль
    from app.auth.utils import get_password_hash
    user_data_dict['password_hash'] = get_password_hash(user_data_dict.pop('password'))

    # Добавление пользователя
    user = await user_dao.add(values=SUserAddDB(**user_data_dict))

    # Пометить токен как использованный
    await tokens_dao.mark_used(token.id, user.id)

    return {'message': 'Вы успешно зарегистрированы!'}


@router.post("/login/")
@limiter.limit("5/minute")  # Ограничение: 5 попыток в минуту
async def auth_user(
        request: Request,
        response: Response,
        user_data: SUserAuth,
        session: AsyncSession = Depends(get_session_without_commit)
) -> dict:
    users_dao = UsersDAO(session)
    user = await users_dao.find_one_or_none(
        filters=UsernameModel(username=user_data.username)
    )

    if not (user and await authenticate_user(user=user, password=user_data.password)):
        raise IncorrectEmailOrPasswordException
    set_tokens(response, user.id)
    return {
        'ok': True,
        'message': 'Авторизация успешна!'
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("user_access_token")
    response.delete_cookie("user_refresh_token")
    return {'message': 'Пользователь успешно вышел из системы'}


@router.get("/me/")
async def get_me(user_data: User = Depends(get_current_user), session: AsyncSession = Depends(get_session_without_commit)) -> SUserInfo:
    return await _user_to_suserinfo(user_data, session)


@router.get("/all_users/")
async def get_all_users(
    page: int = 1,
    per_page: int = 10,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_admin_user)
) -> SUserListResponse:
    """
    Получение списка всех пользователей с пагинацией.
    Доступно для админа (role_id = 3) и суперадмина (role_id = 4).
    
    Примечание: Дублирует /auth/users/, оставлен для обратной совместимости.
    """
    users_dao = UsersDAO(session)
    users, total = await users_dao.find_paginated_with_filters(
        page=page,
        per_page=per_page,
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return SUserListResponse(
        users=[await _user_to_suserinfo(user, session) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("/refresh")
async def process_refresh_token(
        response: Response,
        user: User = Depends(check_refresh_token)
):
    set_tokens(response, user.id)
    return {"message": "Токены успешно обновлены"}


# Эндпоинты для управления пользователями (только для Суперадмина)

@router.get("/users/", response_model=SUserListResponse)
async def get_users(
    page: int = 1,
    per_page: int = 10,
    username: str | None = None,
    email: str | None = None,
    is_active: str | None = None,
    session: AsyncSession = Depends(get_session_without_commit),
    admin: User = Depends(get_current_superadmin_user)
) -> SUserListResponse:
    """
    Получение списка пользователей с пагинацией и фильтрацией.
    Доступно только для Суперадмина (role_id = 4).
    """
    # Преобразуем is_active из строки в bool
    is_active_bool = None
    if is_active is not None and is_active != '':
        is_active_bool = is_active.lower() == 'true'
    
    users_dao = UsersDAO(session)
    users, total = await users_dao.find_paginated_with_filters(
        page=page,
        per_page=per_page,
        username=username,
        email=email,
        is_active=is_active_bool
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return SUserListResponse(
        users=[await _user_to_suserinfo(user, session) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("/users/", response_model=SUserInfo)
async def create_user(
    user_data: SUserCreate,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_superadmin_user)
) -> SUserInfo:
    """
    Создание нового пользователя.
    Доступно только для Суперадмина (role_id = 4).
    """
    users_dao = UsersDAO(session)
    
    # Проверка существования пользователя по username
    existing_user = await users_dao.find_one_or_none(filters=UsernameModel(username=user_data.username))
    if existing_user:
        raise UserAlreadyExistsException
    
    # Проверка существования пользователя по email
    existing_email = await users_dao.find_one_or_none(filters=EmailModel(email=user_data.email))
    if existing_email:
        raise UserAlreadyExistsException
    
    # Хешируем пароль
    password_hash = get_password_hash(user_data.password)
    
    # Создаём пользователя
    from app.auth.schemas import SUserAddDB
    user_dict = user_data.model_dump()
    user_dict.pop('password', None)  # Удаляем обычный пароль
    user_dict['password_hash'] = password_hash
    
    new_user = await users_dao.add(values=SUserAddDB(**user_dict))
    
    # Используем role_id из user_data напрямую, т.к. role ещё не загружена
    role_id = user_data.role_id if user_data.role_id else 1
    
    # Получаем название роли отдельным запросом
    from app.auth.dao import RoleDAO
    role_dao = RoleDAO(session)
    role = await role_dao.find_role_by_id(role_id)
    role_name = role.name if role else "User"
    
    # Формируем данные для SUserInfo
    user_info_dict = {
        'id': new_user.id,
        'username': new_user.username,
        'email': new_user.email,
        'role_id': role_id,
        'role_name': role_name,
        'is_active': new_user.is_active,
        'info': new_user.info,
        'deleted_at': new_user.deleted_at
    }
    
    return SUserInfo(**user_info_dict)


@router.get("/users/{user_id}", response_model=SUserInfo)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session_without_commit),
    admin: User = Depends(get_current_superadmin_user)
) -> SUserInfo:
    """
    Получение пользователя по ID.
    Доступно только для Суперадмина (role_id = 4).
    """
    users_dao = UsersDAO(session)
    user = await users_dao.find_one_or_none_by_id(user_id)
    if not user:
        raise UserNotFoundException
    return await _user_to_suserinfo(user, session)


@router.patch("/users/{user_id}", response_model=SUserInfo)
async def update_user(
    user_id: int,
    user_data: SUserUpdate,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_superadmin_user)
) -> SUserInfo:
    """
    Обновление пользователя.
    Доступно только для Суперадмина (role_id = 4).
    """
    users_dao = UsersDAO(session)
    
    # Проверяем существование пользователя
    user = await users_dao.find_one_or_none_by_id(user_id)
    if not user:
        raise UserNotFoundException
    
    # Подготовка данных для обновления
    update_dict = user_data.model_dump(exclude_unset=True)
    
    # Проверка уникальности username
    if 'username' in update_dict and update_dict['username'] != user.username:
        existing = await users_dao.find_one_or_none(filters=UsernameModel(username=update_dict['username']))
        if existing and existing.id != user_id:
            raise UserAlreadyExistsException
    
    # Проверка уникальности email
    if 'email' in update_dict and update_dict['email'] != user.email:
        existing = await users_dao.find_one_or_none(filters=EmailModel(email=update_dict['email']))
        if existing and existing.id != user_id:
            raise UserAlreadyExistsException
    
    # Обновляем пользователя
    update_values = {k: v for k, v in update_dict.items() if v is not None}
    from sqlalchemy import update
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**update_values)
    )
    await session.execute(stmt)
    await session.flush()
    
    # Получаем обновлённого пользователя
    updated_user = await users_dao.find_one_or_none_by_id(user_id)
    if not updated_user:
        raise UserNotFoundException
    return await _user_to_suserinfo(updated_user, session)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_superadmin_user)
) -> dict:
    """
    Мягкое удаление пользователя.
    Доступно только для Суперадмина (role_id = 4).
    """
    users_dao = UsersDAO(session)
    
    # Проверяем существование пользователя
    user = await users_dao.find_one_or_none_by_id(user_id)
    if not user:
        raise UserNotFoundException
    
    # Нельзя удалить самого себя
    if user_id == admin.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    
    # Мягкое удаление
    await users_dao.soft_delete(user_id)
    return {"message": "Пользователь успешно удалён"}


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    password_data: SPasswordReset,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_superadmin_user)
) -> dict:
    """
    Сброс пароля пользователя.
    Доступно только для Суперадмина (role_id = 4).
    """
    users_dao = UsersDAO(session)
    
    # Проверяем существование пользователя
    user = await users_dao.find_one_or_none_by_id(user_id)
    if not user:
        raise UserNotFoundException
    
    # Хешируем новый пароль
    new_hash = get_password_hash(password_data.new_password)
    
    # Прямое обновление password_hash
    from sqlalchemy import update
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(password_hash=new_hash)
    )
    await session.execute(stmt)
    await session.commit()

    return {"message": "Пароль успешно сброшен"}


@router.get("/keys/", response_model=SRegistrationTokenListResponse)
async def get_keys(
    page: int = 1,
    per_page: int = 10,
    token: str | None = None,
    used: bool | None = None,
    session: AsyncSession = Depends(get_session_without_commit),
    admin: User = Depends(get_current_admin_user)
) -> SRegistrationTokenListResponse:
    """
    Получение списка регистрационных токенов с пагинацией и фильтрами.
    Доступно для админа и выше.
    """
    tokens_dao = RegistrationTokensDAO(session)
    tokens, total = await tokens_dao.find_paginated_with_filters(
        page=page, per_page=per_page, token=token, used=used
    )
    return SRegistrationTokenListResponse(
        tokens=tokens, total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.post("/keys/", response_model=SRegistrationToken)
async def create_key(
    key_data: SRegistrationTokenCreate,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_admin_user)
) -> SRegistrationToken:
    """
    Создание нового регистрационного токена.
    Доступно для админа и выше.
    """
    tokens_dao = RegistrationTokensDAO(session)
    key = await tokens_dao.add(values=key_data)
    return key


@router.put("/keys/{key_id}", response_model=SRegistrationToken)
async def update_key(
    key_id: int,
    key_data: SRegistrationTokenUpdate,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_admin_user)
) -> SRegistrationToken:
    """
    Обновление регистрационного токена.
    Доступно для админа и выше.
    """
    from sqlalchemy import update
    stmt = (
        update(RegistrationTokensDAO.model)
        .where(RegistrationTokensDAO.model.id == key_id)
        .values(**key_data.model_dump(exclude_unset=True))
    )
    await session.execute(stmt)
    await session.commit()

    # Получить обновленный токен
    tokens_dao = RegistrationTokensDAO(session)
    key = await tokens_dao.find_one_or_none_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Токен не найден")
    return key


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: int,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_admin_user)
) -> dict:
    """
    Удаление регистрационного токена.
    Доступно для админа и выше.
    """
    from sqlalchemy import delete
    stmt = delete(RegistrationTokensDAO.model).where(RegistrationTokensDAO.model.id == key_id)
    result = await session.execute(stmt)
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Токен не найден")
    return {"message": "Токен успешно удален"}


@router.post("/keys/generate")
async def generate_keys(
    request: SGenerateKeysRequest,
    session: AsyncSession = Depends(get_session_with_commit),
    admin: User = Depends(get_current_admin_user)
) -> dict:
    """
    Генерация указанного количества регистрационных токенов.
    Доступно для админа и выше.
    """
    tokens_dao = RegistrationTokensDAO(session)
    tokens = await tokens_dao.generate_tokens(request.count)
    await session.commit()

    return {
        "message": f"Сгенерировано {len(tokens)} токенов",
        "tokens": [{"id": t.id, "token": t.token} for t in tokens]
    }

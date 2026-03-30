from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.domain.permissions import Permission, UserContext
from app.presentation.dependencies.permissions import (
    get_ui_flags,
    require_permission,
    get_user_context,
)
from app.presentation.dependencies.game_dep import get_server  # ← Правильно!
from app.domain.permissions import Permission, UserContext

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# =============================================================================
# Публичные страницы
# =============================================================================

@router.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request,
    user_context: UserContext | None = Depends(get_user_context),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Главная страница."""
    return templates.TemplateResponse(
        "home/index.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
        }
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа."""
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
        }
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации."""
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
        }
    )


# =============================================================================
# Страницы управления пользователями
# =============================================================================

@router.get("/users/", response_class=HTMLResponse)
async def users_page(
    request: Request,
    user_context: UserContext = Depends(require_permission(Permission.USERS_VIEW)),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница списка пользователей."""
    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "dynamic": True,
        }
    )


@router.get("/users/create", response_class=HTMLResponse)
async def user_create_page(
    request: Request,
    user_context: UserContext = Depends(require_permission(Permission.USERS_CREATE)),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница создания пользователя."""
    return templates.TemplateResponse(
        "users/create.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "dynamic": True,
        }
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_page(
    request: Request,
    user_id: int,
    user_context: UserContext = Depends(require_permission(Permission.USERS_EDIT)),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница редактирования пользователя."""
    return templates.TemplateResponse(
        "users/edit.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            "user_id": user_id,
            **ui_flags,
            "dynamic": True,
        }
    )


# =============================================================================
# Страницы управления серверами
# =============================================================================

@router.get("/servers/", response_class=HTMLResponse)
async def servers_page(
    request: Request,
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_VIEW_ALL)),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница списка серверов."""
    return templates.TemplateResponse(
        "servers/list.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "dynamic": True,
        }
    )


@router.get("/servers/create", response_class=HTMLResponse)
async def server_create_page(
    request: Request,
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_MANAGE)),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница создания сервера."""
    return templates.TemplateResponse(
        "servers/create.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "dynamic": True,
        }
    )


@router.get("/servers/{server_id}/edit", response_class=HTMLResponse)
async def server_edit_page(
    request: Request,
    server_id: int,
    user_context: UserContext = Depends(require_permission(Permission.SERVERS_MANAGE)),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница редактирования сервера."""
    return templates.TemplateResponse(
        "servers/edit.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            "server_id": server_id,
            **ui_flags,
            "dynamic": True,
        }
    )


# =============================================================================
# Страница "Мои серверы"
# =============================================================================

@router.get("/my-servers/", response_class=HTMLResponse)
async def my_servers_page(
    request: Request,
    user_context: UserContext | None = Depends(get_user_context),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница списка серверов пользователя."""
    if not user_context:
        return RedirectResponse("/login", status_code=303)
    
    return templates.TemplateResponse(
        "servers/my_servers.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "dynamic": True,
        }
    )


# =============================================================================
# Страницы просмотра игры (с использованием dependencies)
# =============================================================================

@router.get("/game/servers/{server_id}/alliances", response_class=HTMLResponse)
async def alliances_page(
    request: Request,
    server_id: int,
    user_context: UserContext = Depends(require_permission(Permission.GAME_VIEW)),
    server = Depends(get_server),  # ← Используем dependency!
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница списка альянсов сервера."""
    if not server:
        return RedirectResponse("/my-servers/")
    
    return templates.TemplateResponse(
        "game/alliances.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "server_id": server_id,
            "server_name": server.name,
            "server_url": server.url,
        }
    )


@router.get("/game/servers/{server_id}/players", response_class=HTMLResponse)
async def players_page(
    request: Request,
    server_id: int,
    user_context: UserContext = Depends(require_permission(Permission.GAME_VIEW)),
    server = Depends(get_server),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница списка игроков сервера."""
    if not server:
        return RedirectResponse("/my-servers/")
    
    return templates.TemplateResponse(
        "game/players.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "server_id": server_id,
            "server_name": server.name,
        }
    )


@router.get("/game/servers/{server_id}/villages", response_class=HTMLResponse)
async def villages_page(
    request: Request,
    server_id: int,
    user_context: UserContext = Depends(require_permission(Permission.GAME_VIEW)),
    server = Depends(get_server),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница списка деревень сервера."""
    if not server:
        return RedirectResponse("/my-servers/")
    
    return templates.TemplateResponse(
        "game/villages.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "server_id": server_id,
            "server_name": server.name,
        }
    )


@router.get("/game/servers/{server_id}/map-search", response_class=HTMLResponse)
async def map_search_page(
    request: Request,
    server_id: int,
    user_context: UserContext = Depends(require_permission(Permission.GAME_VIEW)),
    server = Depends(get_server),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница поиска клеток карты сервера."""
    if not server:
        return RedirectResponse("/my-servers/")

    return templates.TemplateResponse(
        "game/map_search.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "server_id": server_id,
            "server_name": server.name,
            "server_url": server.url,
        }
    )


# =============================================================================
# Страницы управления ключами
# =============================================================================

@router.get("/keys", response_class=HTMLResponse)
async def keys_page(
    request: Request,
    user_context: UserContext = Depends(require_permission(Permission.KEYS_VIEW)),
    ui_flags: dict = Depends(get_ui_flags),
):
    """Страница управления регистрационными ключами."""
    return templates.TemplateResponse(
        "auth/keys.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": user_context,
            **ui_flags,
            "dynamic": True,
        }
    )


@router.get("/users/keys", response_class=HTMLResponse)
async def users_keys_page(
    request: Request,
    user_context: UserContext = Depends(require_permission(Permission.KEYS_VIEW)),
):
    """Алиас для страницы ключей."""
    return RedirectResponse("/keys")
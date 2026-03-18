from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.auth.models import User
from app.dependencies.auth_dep import get_current_user, get_current_admin_user, get_current_superadmin_user
from app.game.router import _check_admin_or_moderator

# Создаём роутер
router = APIRouter()

# Инициализируем Jinja2Templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """
    Главная страница. Доступна без авторизации.
    """
    return templates.TemplateResponse(
        "home/index.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user": None,  # Будет загружено через JavaScript
        }
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Страница входа.
    """
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
        }
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Страница регистрации.
    """
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
        }
    )


@router.get("/users/", response_class=HTMLResponse)
async def users_page(request: Request, admin: User = Depends(get_current_superadmin_user)):
    """
    Страница списка пользователей. Требует авторизации и прав суперадмина.
    """
    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "dynamic": True,
        }
    )


@router.get("/users/create", response_class=HTMLResponse)
async def user_create_page(request: Request, admin: User = Depends(get_current_superadmin_user)):
    """
    Страница создания пользователя. Требует авторизации и прав суперадмина.
    """
    return templates.TemplateResponse(
        "users/create.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "dynamic": True,
        }
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_page(request: Request, user_id: int, admin: User = Depends(get_current_superadmin_user)):
    """
    Страница редактирования пользователя. Требует авторизации и прав суперадмина.
    """
    return templates.TemplateResponse(
        "users/edit.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "user_id": user_id,
            "dynamic": True,
        }
    )


# === Страницы серверов ===

@router.get("/servers/", response_class=HTMLResponse)
async def servers_page(request: Request, user: User = Depends(_check_admin_or_moderator)):
    """
    Страница списка серверов. Требует авторизации и прав админа или модератора.
    """
    return templates.TemplateResponse(
        "servers/list.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "dynamic": True,
        }
    )


@router.get("/servers/create", response_class=HTMLResponse)
async def server_create_page(request: Request, user: User = Depends(_check_admin_or_moderator)):
    """
    Страница создания сервера. Требует авторизации и прав админа или модератора.
    """
    return templates.TemplateResponse(
        "servers/create.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "dynamic": True,
        }
    )


@router.get("/servers/{server_id}/edit", response_class=HTMLResponse)
async def server_edit_page(request: Request, server_id: int, user: User = Depends(_check_admin_or_moderator)):
    """
    Страница редактирования сервера. Требует авторизации и прав админа или модератора.
    """
    return templates.TemplateResponse(
        "servers/edit.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "server_id": server_id,
            "dynamic": True,
        }
    )


# === Страница "Мои серверы" ===

@router.get("/my-servers/", response_class=HTMLResponse)
async def my_servers_page(request: Request, user: User = Depends(get_current_user)):
    """
    Страница списка серверов пользователя. Требует авторизации.
    """
    return templates.TemplateResponse(
        "servers/my_servers.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "dynamic": True,
        }
    )


# === Страницы просмотра игры ===

@router.get("/game/servers/{server_id}/alliances", response_class=HTMLResponse)
async def alliances_page(request: Request, server_id: int, user: User = Depends(get_current_user)):
    """
    Страница списка альянсов сервера. Требует авторизации.
    """
    from app.game.dao import ServerDAO
    from app.dao.database import async_session_maker
    
    async with async_session_maker() as session:
        server_dao = ServerDAO(session)
        server = await server_dao.find_one_or_none_by_id(server_id)
        
    if not server:
        return RedirectResponse("/my-servers/")
    
    return templates.TemplateResponse(
        "game/alliances.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "server_id": server_id,
            "server_name": server.name,
            "server_url": server.url,
            # "dynamic": True,
        }
    )


@router.get("/game/servers/{server_id}/players", response_class=HTMLResponse)
async def players_page(request: Request, server_id: int, user: User = Depends(get_current_user)):
    """
    Страница списка игроков сервера. Требует авторизации.
    """
    from app.game.dao import ServerDAO
    from app.dao.database import async_session_maker
    
    async with async_session_maker() as session:
        server_dao = ServerDAO(session)
        server = await server_dao.find_one_or_none_by_id(server_id)
        
    if not server:
        return RedirectResponse("/my-servers/")
    
    return templates.TemplateResponse(
        "game/players.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "server_id": server_id,
            "server_name": server.name,
            # "dynamic": True,
        }
    )


@router.get("/game/servers/{server_id}/villages", response_class=HTMLResponse)
async def villages_page(request: Request, server_id: int, user: User = Depends(get_current_user)):
    """
    Страница списка деревень сервера. Требует авторизации.
    """
    from app.game.dao import ServerDAO
    from app.dao.database import async_session_maker
    
    async with async_session_maker() as session:
        server_dao = ServerDAO(session)
        server = await server_dao.find_one_or_none_by_id(server_id)
        
    if not server:
        return RedirectResponse("/my-servers/")
    
    return templates.TemplateResponse(
        "game/villages.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "server_id": server_id,
            "server_name": server.name,
            # "dynamic": True,
        }
    )


@router.get("/game/servers/{server_id}/map-search", response_class=HTMLResponse)
async def map_search_page(request: Request, server_id: int, user: User = Depends(get_current_user)):
    """
    Страница поиска клеток карты сервера. Требует авторизации.
    """
    from app.game.dao import ServerDAO
    from app.dao.database import async_session_maker

    async with async_session_maker() as session:
        server_dao = ServerDAO(session)
        server = await server_dao.find_one_or_none_by_id(server_id)

    if not server:
        return RedirectResponse("/my-servers/")

    return templates.TemplateResponse(
        "game/map_search.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "server_id": server_id,
            "server_name": server.name,
            "server_url": server.url,
            # "dynamic": True,
        }
    )

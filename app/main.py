import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, APIRouter, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth.router import router as router_auth
from app.views.router import router as router_views
from app.game.router import router as router_game
from app.map.router import router as router_map
from app.limiter import limiter
from app.config import settings

# Разрешённые источники для CORS (из переменной окружения или значения по умолчанию)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000"
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Инициализация приложения...")
    
    # Запуск scheduler если включен
    from app.services.scheduler import scheduler
    if settings.SCHEDULER_ENABLED:
        try:
            await scheduler.start()
            logger.info("Планировщик обновлений карты запущен")
        except Exception as e:
            logger.warning(f"Не удалось запустить планировщик: {e}")
    
    yield
    
    # Остановка scheduler
    if settings.SCHEDULER_ENABLED:
        try:
            await scheduler.shutdown()
            logger.info("Планировщик обновлений карты остановлен")
        except Exception as e:
            logger.warning(f"Не удалось остановить планировщик: {e}")
    
    logger.info("Завершение работы приложения...")


def create_app() -> FastAPI:
    """
   Создание и конфигурация FastAPI приложения.

   Returns:
       Сконфигурированное приложение FastAPI
   """
    app = FastAPI(
        title="Стартовая сборка FastAPI",
        description=(
            "Стартовая сборка с интегрированной SQLAlchemy 2 для разработки FastAPI приложений с продвинутой "
            "архитектурой, включающей авторизацию, аутентификацию и управление ролями пользователей.\n\n"
            "**Автор проекта**: Яковенко Алексей\n"
            "**Telegram**: https://t.me/PythonPathMaster"
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Добавляем rate limiter
    app.state.limiter = limiter

    # Обработчик исключений rate limiting
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Слишком много запросов. Попробуйте позже."}
        )

    # Обработчик исключений 401 - переадресация на страницу логина для HTML-запросов
    @app.exception_handler(401)
    async def unauthorized_handler(request: Request, exc):
        """Переадресация на /login при отсутствии авторизации для HTML-страниц."""
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            return RedirectResponse(url="/login", status_code=302)
        # Для API-запросов возвращаем стандартный JSON-ответ
        return await http_exception_handler(request, exc)

    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # для разработки
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # allow_origins=ALLOWED_ORIGINS,
        # allow_credentials=True,
        # allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        # allow_headers=["Content-Type", "Authorization", "Cookie"],
    )

    # Монтирование статических файлов
    app.mount(
        '/static',
        StaticFiles(directory='app/static'),
        name='static'
    )

    # Регистрация роутеров
    register_routers(app)

    return app


def register_routers(app: FastAPI) -> None:
    """Регистрация роутеров приложения."""
    # Корневой роутер
    root_router = APIRouter()

    @root_router.get("/", tags=["root"])
    def home_page():
        return {
            "message": "Добро пожаловать! Проект создан для сообщества 'Легкий путь в Python'.",
            "community": "https://t.me/PythonPathMaster",
            "author": "Яковенко Алексей"
        }

    # Подключение роутеров
    app.include_router(router_auth, prefix='/auth', tags=['Auth'])
    app.include_router(router_views, tags=["views"])
    app.include_router(router_game, prefix='/game', tags=['Game'])
    app.include_router(router_map, tags=["Map"])
    app.include_router(root_router, tags=["root"])


# Создание экземпляра приложения
app = create_app()

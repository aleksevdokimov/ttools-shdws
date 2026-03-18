"""
Сервис планировщика для автоматических обновлений карты.

Этот сервис использует APScheduler для планирования периодических обновлений карты для всех активных серверов.
"""
# import logging
import os
from typing import Optional
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.database import async_session_maker
from app.game.models import Server
from app.services.map_update import map_update_service, ConcurrentUpdateError

# logger = logging.getLogger(__name__)


class MapUpdateScheduler:
    """
    Планировщик для автоматических обновлений карты.
    
    Возможности:
    - Периодические обновления для каждого активного сервера
    - Настраиваемые интервалы обновлений
    - Обработка ошибок и логирование
    - Поддержка ручного запуска
    """
    
    def __init__(self, scheduler: Optional[AsyncIOScheduler] = None):
        self.scheduler = scheduler or AsyncIOScheduler()
        self._is_running = False
        
    async def start(self) -> None:
        """Запуск планировщика."""
        if not self._is_running:
            # Запланировать обновление для всех активных серверов каждый час
            self.scheduler.add_job(
                self.update_all_servers,
                trigger=IntervalTrigger(hours=1),
                id='update_all_servers',
                name='Update all server maps',
                replace_existing=True
            )
            
            self.scheduler.start()
            self._is_running = True
            logger.info("Map update scheduler started")
            
    async def shutdown(self) -> None:
        """Остановка планировщика."""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Map update scheduler stopped")
            
    async def update_all_servers(self) -> dict:
        """
        Обновить данные карты для всех активных серверов.
        
        Возвращает:
            Словарь с результатами обновления для каждого сервера
        """
        results = {}
        
        async with async_session_maker() as session:
            # Получить все активные серверы
            result = await session.execute(
                select(Server).where(Server.is_active == True)
            )
            servers = result.scalars().all()
            
        logger.info(f"Starting map update for {len(servers)} servers")
        
        for server in servers:
            try:
                # Создать URL для map.sql
                map_url = self._get_map_url(server.url)
                
                if map_url:
                    # Загрузить и распарсить данные карты (с сохранением в историю)
                    data = await map_update_service.download_and_parse_map_file(map_url)
                    
                    # Обновить данные сервера
                    stats = await map_update_service.update_server_data(server.id, data)
                    
                    results[server.id] = {
                        'status': 'success',
                        'server_name': server.name,
                        'stats': stats
                    }
                    logger.info(
                        f"Updated server {server.name}: "
                        f"{stats['villages_processed']} villages, "
                        f"{stats['players_processed']} players, "
                        f"{stats['alliances_processed']} alliances"
                    )
                else:
                    results[server.id] = {
                        'status': 'skipped',
                        'server_name': server.name,
                        'reason': 'No map.sql URL could be constructed'
                    }
                    
            except ConcurrentUpdateError:
                results[server.id] = {
                    'status': 'skipped',
                    'server_name': server.name,
                    'reason': 'Server is already being updated'
                }
                logger.warning(f"Server {server.name} is already being updated, skipping")
                
            except Exception as e:
                results[server.id] = {
                    'status': 'error',
                    'server_name': server.name,
                    'error': str(e)
                }
                logger.error(f"Failed to update server {server.name}: {e}")
                
        return results
        
    async def update_server(self, server_id: int) -> dict:
        """
        Обновить данные карты для конкретного сервера.
        
        Параметры:
            server_id: ID сервера для обновления
            
        Возвращает:
            Словарь с результатом обновления
        """
        async with async_session_maker() as session:
            # Получить сервер
            result = await session.execute(
                select(Server).where(Server.id == server_id)
            )
            server = result.scalar_one_or_none()
            
        if not server:
            return {
                'status': 'error',
                'error': f'Server {server_id} not found'
            }
            
        if not server.is_active:
            return {
                'status': 'error',
                'error': f'Server {server.name} is not active'
            }
            
        try:
            # Создать URL для map.sql
            map_url = self._get_map_url(server.url)
            
            if not map_url:
                return {
                    'status': 'error',
                    'error': 'No map.sql URL could be constructed'
                }
                
            # Загрузить и распарсить данные карты (с сохранением в историю)
            data = await map_update_service.download_and_parse_map_file(map_url)
            
            # Обновить данные сервера
            stats = await map_update_service.update_server_data(server_id, data)
            
            return {
                'status': 'success',
                'server_name': server.name,
                'stats': stats
            }
            
        except ConcurrentUpdateError:
            return {
                'status': 'error',
                'error': 'Server is already being updated'
            }
        except Exception as e:
            logger.error(f"Failed to update server {server.name}: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _get_map_url(self, server_url: str) -> Optional[str]:
        """
        Создать URL для map.sql из URL сервера.
        
        Параметры:
            server_url: Базовый URL Travian-сервера
            
        Возвращает:
            URL к map.sql или None, если невозможно определить
        """
        # Попробовать стандартные пути расположения map.sql
        base_url = server_url.rstrip('/')
        
        # Стандартные шаблоны для расположения map.sql
        map_paths = [
            '/map.sql',
        ]
        
        for path in map_paths:
            return f"{base_url}{path}"
            
        return None
        
    def add_server_job(self, server_id: int, cron: Optional[str] = None) -> None:
        """
        Добавить выделенное задание для конкретного сервера.
        
        Параметры:
            server_id: ID сервера
            cron: Cron-выражение для расписания (например, '0 * * * *')
        """
        job_id = f'update_server_{server_id}'
        
        if cron:
            # Разобрать cron-выражение
            parts = cron.split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4]
                )
            else:
                trigger = IntervalTrigger(hours=1)
        else:
            trigger = IntervalTrigger(hours=1)
            
        self.scheduler.add_job(
            self._update_single_server,
            trigger=trigger,
            args=[server_id],
            id=job_id,
            name=f'Update server {server_id}',
            replace_existing=True
        )
        logger.info(f"Added update job for server {server_id}")
        
    def remove_server_job(self, server_id: int) -> None:
        """
        Удалить выделенное задание для конкретного сервера.
        
        Параметры:
            server_id: ID сервера
        """
        job_id = f'update_server_{server_id}'
        self.scheduler.remove_job(job_id)
        logger.info(f"Removed update job for server {server_id}")
        
    async def _update_single_server(self, server_id: int) -> None:
        """
        Внутренний метод для обновления одного сервера.
        
        Параметры:
            server_id: ID сервера для обновления
        """
        await self.update_server(server_id)


# Singleton instance
scheduler = MapUpdateScheduler()

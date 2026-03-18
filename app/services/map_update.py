"""
Сервис обновления карты для синхронизации данных сервера Travian.

Этот сервис обрабатывает:
- Загрузка и парсинг файлов map.sql
- Синхронизация альянсов, игроков и деревень
- Использование PostgreSQL advisory locks для защиты от параллельных обновлений ???
- Логирование операций обновления
"""
import asyncio
# import logging
import time
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.dao.database import async_session_maker
from app.game.models import Server, MapUpdate, Alliance, Player, Village
from app.services.map_parser import download_and_save_map_file
from app.config import settings

# logger = logging.getLogger(__name__)


class MapUpdateError(Exception):
    """Исключение, выбрасываемое при ошибке обновления карты."""
    pass


class ConcurrentUpdateError(Exception):
    """Исключение, выбрасываемое когда другое обновление уже выполняется."""
    pass


class MapUpdateService:
    """
    Сервис для обновления данных карты сервера из файлов Travian map.sql.
    """
    
    # Advisory lock ID для защиты от параллельных обновлений
    LOCK_BASE = 1000000
    
    def __init__(self):
        self._lock = asyncio.Lock()
        
    async def download_and_parse_map_file(self, url: str) -> list[dict]:
        """
        Загрузка и анализ файла map.sql по URL-адресу.
        Аргументы:
            url: URL-адрес для загрузки файла map.sql
        Возвращает:
            Список проанализированных записей о деревнях
        """    
        # Загрузка с сохранением файла
        all_records = []
        
        async for batch in download_and_save_map_file(url):
            all_records.extend(batch)
            
        logger.info(f"Parsed {len(all_records)} village records from {url}")
        return all_records
        
    async def update_server_data(self, server_id: int, data: list[dict]) -> dict:
        """
        Обновляет все данные сервера на основе разобранных записей карты.
        Аргументы:
            server_id: ID сервера для обновления
            data: Разобранные записи о деревне из файла map.sql
        Возвращает:
            Словарь со статистикой обновлений
        """
        async with async_session_maker() as session:
            try:
                # Попытка получить advisory lock
                if not await self._acquire_lock(session, server_id):
                    raise ConcurrentUpdateError(
                        f"Server {server_id} is already being updated"
                    )
                    
                # Создать запись в логе обновлений
                update_id = await self._create_update_log(session, server_id)
                
                # Отметить сервер как обновляющийся
                await self._mark_server_updating(session, server_id, True)
                
                start_time = time.time()
                stats = {
                    'villages_processed': 0,
                    'players_processed': 0,
                    'alliances_processed': 0,
                }
                
                try:
                    # Сначала синхронизировать альянсы
                    alliances_count = await self._sync_alliances(session, server_id, data)
                    stats['alliances_processed'] = alliances_count
                    
                    # Синхронизировать игроков
                    players_count = await self._sync_players(session, server_id, data)
                    stats['players_processed'] = players_count
                    
                    # Синхронизировать деревни
                    villages_count = await self._sync_villages(session, server_id, data)
                    stats['villages_processed'] = villages_count
                    
                    # Обновить агрегаты
                    await self._update_aggregates(session, server_id)
                    
                    # Логировать успешное завершение
                    duration_ms = int((time.time() - start_time) * 1000)
                    await self._complete_update_log(
                        session, update_id, 'completed', stats, duration_ms
                    )
                    
                except Exception as e:
                    # Логировать неудачу
                    await self._complete_update_log(
                        session, update_id, 'failed', stats, 
                        error_message=str(e)
                    )
                    raise
                    
            finally:
                # Освободить блокировку и отметить сервер как необновляющийся
                await self._mark_server_updating(session, server_id, False)
                await self._release_lock(session, server_id)
                
        return stats
        
    async def _acquire_lock(self, session: AsyncSession, server_id: int) -> bool:
        """
        Попытка получить advisory lock для сервера.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера для блокировки
            
        Возвращает:
            True, если блокировка получена, иначе False
        """
        # SQLite не поддерживает advisory locks, пропускаем блокировку
        if not settings.DB_URL or not settings.DB_URL.startswith('postgresql'):
            return True
            
        lock_id = self.LOCK_BASE + server_id
        result = await session.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": lock_id}
        )
        return bool(result.scalar())
        
    async def _release_lock(self, session: AsyncSession, server_id: int) -> bool:
        """
        Освободить advisory lock для сервера.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера для разблокировки
            
        Возвращает:
            True, если блокировка освобождена
        """
        # SQLite не поддерживает advisory locks, пропускаем разблокировку
        if not settings.DB_URL or not settings.DB_URL.startswith('postgresql'):
            return True
            
        lock_id = self.LOCK_BASE + server_id
        await session.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": lock_id}
        )
        return True
        
    async def _create_update_log(
        self, 
        session: AsyncSession, 
        server_id: int
    ) -> int:
        """
        Создать новую запись в логе обновлений.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера
            
        Возвращает:
            ID созданной записи лога
        """
        result = await session.execute(
            text("""
                INSERT INTO server_map_updates (server_id, started_at, status)
                VALUES (:server_id, :started_at, 'running')
                RETURNING id
            """),
            {
                "server_id": server_id,
                "started_at": datetime.utcnow()
            }
        )
        await session.commit()
        return result.scalar()
        
    async def _complete_update_log(
        self,
        session: AsyncSession,
        update_id: int,
        status: str,
        stats: dict,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Обновить запись лога обновлений со статусом завершения.
        
        Параметры:
            session: Сессия базы данных
            update_id: ID записи лога
            status: Статус (completed/failed)
            stats: Словарь статистики
            duration_ms: Продолжительность в миллисекундах
            error_message: Сообщение об ошибке в случае неудачи
        """
        await session.execute(
            text("""
                UPDATE server_map_updates
                SET finished_at = :finished_at,
                    status = :status,
                    villages_processed = :villages,
                    players_processed = :players,
                    alliances_processed = :alliances,
                    duration_ms = :duration_ms,
                    error_message = :error_message
                WHERE id = :update_id
            """),
            {
                "update_id": update_id,
                "finished_at": datetime.utcnow(),
                "status": status,
                "villages": stats.get('villages_processed', 0),
                "players": stats.get('players_processed', 0),
                "alliances": stats.get('alliances_processed', 0),
                "duration_ms": duration_ms,
                "error_message": error_message
            }
        )
        await session.commit()
        
    async def _mark_server_updating(
        self, 
        session: AsyncSession, 
        server_id: int, 
        is_updating: bool
    ) -> None:
        """
        Отметить сервер как обновляющийся/необновляющийся.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера
            is_updating: Обновляется ли сервер
        """
        if is_updating:
            await session.execute(
                text("""
                    UPDATE servers
                    SET is_updating = TRUE,
                        last_update_started_at = :started_at
                    WHERE id = :server_id
                """),
                {"server_id": server_id, "started_at": datetime.utcnow()}
            )
        else:
            await session.execute(
                text("""
                    UPDATE servers
                    SET is_updating = FALSE,
                        last_update_finished_at = :finished_at,
                        last_update_info = :finished_at
                    WHERE id = :server_id
                """),
                {"server_id": server_id, "finished_at": datetime.utcnow()}
            )
        await session.commit()
        
    async def _sync_alliances(
        self,
        session: AsyncSession,
        server_id: int,
        data: list[dict]
    ) -> int:
        """
        Синхронизировать альянсы из данных карты.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера
            data: Проанализированные записи деревень
            
        Возвращает:
            Количество обработанных альянсов
        """
        # Извлечь уникальные альянсы из данных
        alliances = {}
        for record in data:
            if record.get('alliance_id'):
                alliance_id = record['alliance_id']
                if alliance_id not in alliances:
                    alliances[alliance_id] = {
                        'alliance_id': alliance_id,
                        'tag': record.get('alliance_tag'),
                        'name': record.get('alliance_name'),
                        'player_names': []
                    }
                if record.get('player_name'):
                    alliances[alliance_id]['player_names'].append(record['player_name'])
        
        # UPSERT альянсов
        for alliance_id, alliance_data in alliances.items():
            await session.execute(
                text("""
                    INSERT INTO alliances (server_id, alliance_id, tag, name, last_seen_at)
                    VALUES (:server_id, :alliance_id, :tag, :name, :last_seen_at)
                    ON CONFLICT (server_id, alliance_id) DO UPDATE SET
                        tag = EXCLUDED.tag,
                        name = EXCLUDED.name,
                        last_seen_at = EXCLUDED.last_seen_at
                """),
                {
                    "server_id": server_id,
                    "alliance_id": alliance_id,
                    "tag": alliance_data['tag'],
                    "name": alliance_data['name'],
                    "last_seen_at": datetime.utcnow()
                }
            )
            
        await session.commit()
        return len(alliances)
        
    async def _sync_players(
        self,
        session: AsyncSession,
        server_id: int,
        data: list[dict]
    ) -> int:
        """
        Синхронизировать игроков из данных карты.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера
            data: Проанализированные записи деревень
            
        Возвращает:
            Количество обработанных игроков
        """
        # Извлечь уникальных игроков из данных
        players = {}
        for record in data:
            if record.get('player_name'):
                if record['player_name'] not in players:
                    players[record['player_name']] = {
                        'account_id': record['account_id'],
                        'name': record['player_name'],
                        'alliance_tag': record.get('alliance_tag'),
                        'race_id': record.get('race_id'),
                        'population': record.get('population', 0)
                    }
                else:
                    # Накопить население
                    players[record['player_name']]['population'] += record.get('population', 0)
        
        # Получить ID альянсов для этого сервера
        alliance_map = await self._get_alliance_map(session, server_id)
        
        # UPSERT игроков
        for player_name, player_data in players.items():
            alliance_id = None
            if player_data['alliance_tag']:
                alliance_id = alliance_map.get(player_data['alliance_tag'])
                
            await session.execute(
                text("""
                    INSERT INTO players (server_id, account_id, name, alliance_id, race_id, population, last_seen_at)
                    VALUES (:server_id, :account_id, :name, :alliance_id, :race_id, :population, :last_seen_at)
                    ON CONFLICT (server_id, account_id) DO UPDATE SET
                        alliance_id = EXCLUDED.alliance_id,
                        race_id = COALESCE(EXCLUDED.race_id, players.race_id),
                        population = EXCLUDED.population,
                        last_seen_at = EXCLUDED.last_seen_at
                """),
                {
                    "server_id": server_id,
                    "account_id": player_data["account_id"],  # ← обязательно
                    "name": player_name,
                    "alliance_id": alliance_id,
                    "race_id": player_data['race_id'],
                    "population": player_data['population'],
                    "last_seen_at": datetime.utcnow()
                }
            )
            
        await session.commit()
        return len(players)
        
    async def _sync_villages(
        self,
        session: AsyncSession,
        server_id: int,
        data: list[dict]
    ) -> int:
        """
        Синхронизировать деревни из данных карты.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера
            data: Проанализированные записи деревень
            
        Возвращает:
            Количество обработанных деревень
        """
        # Получить ID игроков для этого сервера
        player_map = await self._get_player_map(session, server_id)
        
        # UPSERT деревень
        for record in data:
            player_id = None
            if record.get('player_name'):
                player_id = player_map.get(record['player_name'])
                
            await session.execute(
                text("""
                    INSERT INTO villages 
                    (server_id, village_id, map_id, name, x, y, player_id, race_id, population, last_seen_at)
                    VALUES 
                    (:server_id, :village_id, :map_id, :name, :x, :y, :player_id, :race_id, :population, :last_seen_at)
                    ON CONFLICT (server_id, village_id) DO UPDATE SET
                        map_id = EXCLUDED.map_id,
                        name = EXCLUDED.name,
                        x = EXCLUDED.x,
                        y = EXCLUDED.y,
                        player_id = EXCLUDED.player_id,
                        population = EXCLUDED.population,
                        last_seen_at = EXCLUDED.last_seen_at
                """),
                {
                    "server_id": server_id,
                    "village_id": record.get('village_id'),
                    "map_id": record.get('map_id'),
                    "name": record.get('village_name'),
                    "x": record.get('x'),
                    "y": record.get('y'),
                    "player_id": player_id,
                    "race_id": record.get('race_id'),
                    "population": record.get('population'),
                    "last_seen_at": datetime.utcnow()
                }
            )
            
        await session.commit()
        return len(data)
        
    async def _update_aggregates(
        self,
        session: AsyncSession,
        server_id: int
    ) -> None:
        """
        Обновить агрегированные счётчики для игроков и альянсов.
        
        Параметры:
            session: Сессия базы данных
            server_id: ID сервера
        """
        # Обновить villages_count для игроков
        await session.execute(
            text("""
                UPDATE players
                SET villages_count = sub.cnt
                FROM (
                    SELECT player_id, COUNT(*) as cnt
                    FROM villages
                    WHERE server_id = :server_id AND player_id IS NOT NULL
                    GROUP BY player_id
                ) sub
                WHERE players.id = sub.player_id
            """),
            {"server_id": server_id}
        )
        
        # Обновить population и players_count для альянсов
        await session.execute(
            text("""
                UPDATE alliances
                SET 
                    population = sub.population,
                    players_count = sub.players_count
                FROM (
                    SELECT 
                        alliance_id,
                        SUM(population) as population,
                        COUNT(DISTINCT id) as players_count
                    FROM players
                    WHERE server_id = :server_id AND alliance_id IS NOT NULL
                    GROUP BY alliance_id
                ) sub
                WHERE alliances.id = sub.alliance_id
            """),
            {"server_id": server_id}
        )
        
        await session.commit()
        
    async def _get_alliance_map(
        self,
        session: AsyncSession,
        server_id: int
    ) -> dict[str, int]:
        """Get alliance tag to ID mapping."""
        result = await session.execute(
            text("SELECT tag, id FROM alliances WHERE server_id = :server_id"),
            {"server_id": server_id}
        )
        return {row[0]: row[1] for row in result.fetchall()}
        
    async def _get_player_map(
        self,
        session: AsyncSession,
        server_id: int
    ) -> dict[str, int]:
        """Get player name to ID mapping."""
        result = await session.execute(
            text("SELECT name, id FROM players WHERE server_id = :server_id"),
            {"server_id": server_id}
        )
        return {row[0]: row[1] for row in result.fetchall()}
        
    async def get_last_update_status(
        self,
        server_id: int
    ) -> Optional[dict]:
        """
        Get the status of the last update for a server.
        
        Args:
            server_id: Server ID
            
        Returns:
            Dictionary with update status or None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT id, started_at, finished_at, status, 
                           villages_processed, players_processed, alliances_processed,
                           error_message, duration_ms
                    FROM server_map_updates
                    WHERE server_id = :server_id
                    ORDER BY started_at DESC
                    LIMIT 1
                """),
                {"server_id": server_id}
            )
            row = result.fetchone()
            if row:
                return {
                    'id': row[0],
                    'started_at': row[1].isoformat() if row[1] else None,
                    'finished_at': row[2].isoformat() if row[2] else None,
                    'status': row[3],
                    'villages_processed': row[4],
                    'players_processed': row[5],
                    'alliances_processed': row[6],
                    'error_message': row[7],
                    'duration_ms': row[8]
                }
            return None


# Singleton instance
map_update_service = MapUpdateService()

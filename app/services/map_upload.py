"""
Сервис для загрузки и сохранения данных карты из внешнего API.

Этот сервис обрабатывает:
- Приём данных тайлов карты от внешнего источника
- Сохранение данных в JSON формате в директорию map_history
- Логирование операций загрузки
- Сохранение данных карты в БД (таблица maps)
"""
import os
import json
# import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from app.config import settings
from app.game.schemas import Tile, TilesBatch
from app.game.models import TypeField
from app.dao.database import async_session_maker

# logger = logging.getLogger(__name__)


class MapUploadService:
    """
    Сервис для загрузки и сохранения данных карты.
    """
    
    def __init__(self):
        self._history_dir = Path(settings.BASE_DIR) / "app" / "map_history"
        # Создаём директорию, если не существует
        self._history_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, server: str) -> str:
        """
        Генерирует имя файла по аналогии с существующими.
        
        Формат: YYYYMMDD_HHMMSS_server_url.json
        
        Пример: 20260310_175134_ts100_x10_europe_travian_com.json
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        
        # Очищаем URL от протокола и спецсимволов
        server_clean = server.replace("https://", "").replace("http://", "")
        server_clean = server_clean.replace(".", "_").replace("/", "_").replace(":", "_")
        
        return f"{timestamp}_{server_clean}.json"
    
    def _prepare_tile_data(self, tile: Tile) -> Dict[str, Any]:
        """
        Подготавливает данные тайла для сохранения.
        """
        return {
            "position": {
                "x": tile.position.x,
                "y": tile.position.y
            },
            "text": tile.text,
            "title": tile.title,
            "aid": tile.aid,
            "did": tile.did,
            "uid": tile.uid
        }
    
    async def save_tiles(self, batch: TilesBatch) -> Dict[str, Any]:

        from sqlalchemy import select
        from app.game.models import Server

        logger.info("Begin save")

        filename = self._generate_filename(batch.server)
        filepath = self._history_dir / filename

        data = {
            "server": batch.server,
            "uploaded_at": datetime.now().isoformat(),
            "tiles_count": len(batch.tiles),
            "tiles": [self._prepare_tile_data(tile) for tile in batch.tiles]
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Сохранены данные карты для сервера {batch.server}. ")
        logger.info(f"Количество тайлов: {len(batch.tiles)}, файл: {filename}")

        # ---- получаем server_id ----
        async with async_session_maker() as session:
            result = await session.execute(
                select(Server).where(Server.name == batch.server)
            )
            server = result.scalar_one_or_none()

            if not server:
                raise ValueError(f"Server '{batch.server}' not found in DB")

            server_id = server.id

        # ---- сохраняем в БД ----
        db_result = await self.save_tiles_to_db(batch, server_id)

        return {
            "filename": filename,
            "filepath": str(filepath),
            "tiles_count": len(batch.tiles),
            "db_saved_tiles": db_result["tiles_count"]
        }
    
    def _determine_field_type_name(self, title: Optional[str], text: Optional[str]) -> str | None:
        """
        Определяет название типа поля на основе title и text.
        
        Логика:
        - Oasis определяется по наличию {k.fo} в title
        - Field определяется по {k.vt} {k.f1-f12} или {k.dt}
        - Остальные типы: Forest, Lake, Mountain, Clay
        - Бонусы оазисов определяются по text
        
        Аргументы:
            title: Заголовок тайла
            text: Текст тайла
            
        Возвращает:
            Название типа поля
        """
        if not title:
            return None  # По умолчанию
        
        # Oasis - проверяем бонусы
        if "{k.fo}" in title or "{k.bt}" in title:
            if not self._determine_oasis_type(text) == "Unknown oasis":
                return self._determine_oasis_type(text)
        
        # Field types
        if "{k.vt}" in title and "{k.f1}" in title:
            return "Field 3-3-3-9"
        elif "{k.vt}" in title and "{k.f2}" in title:
            return "Field 3-4-5-6"
        elif "{k.vt}" in title and "{k.f3}" in title:
            return "Field 4-4-4-6"
        elif "{k.vt}" in title and "{k.f4}" in title:
            return "Field 4-5-3-6"
        elif "{k.vt}" in title and "{k.f5}" in title:
            return "Field 5-3-4-6"
        elif "{k.vt}" in title and "{k.f6}" in title:
            return "Field 1-1-1-15"
        elif "{k.vt}" in title and "{k.f7}" in title:
            return "Field 4-4-3-7"
        elif "{k.vt}" in title and "{k.f8}" in title:
            return "Field 3-4-4-7"
        elif "{k.vt}" in title and "{k.f9}" in title:
            return "Field 4-3-4-7"
        elif "{k.vt}" in title and "{k.f10}" in title:
            return "Field 3-5-4-6"
        elif "{k.vt}" in title and "{k.f11}" in title:
            return "Field 4-3-5-6"
        elif "{k.vt}" in title and "{k.f12}" in title:
            return "Field 5-4-3-6"
        elif "{k.dt}" in title:
            return "Field 4-4-4-6"
        
        # Остальные типы
        title_lower = title.lower()
        if "forest" in title_lower:
            return "Forest"
        elif "lake" in title_lower:
            return "Lake"
        elif "mountain" in title_lower:
            return "Mountain"
        elif "clay" in title_lower:
            return "Clay"
        elif "vulcano" in title_lower:
            return "Vulcano"
        
        return None  # По умолчанию
    
    def _determine_oasis_type(self, text: Optional[str]) -> str:
        """
        Определяет тип оазиса на основе text (бонусы).
        Поддерживаются форматы:
        - Одиночные бонусы 25% и 50%: wood/clay/iron/crop
        - Двойные бонусы: ресурс 25% + crop 25%
        - Отдельно crop 50%
        """

        if not text:
            return "Unknown oasis"

        has_r1 = "r1" in text
        has_r2 = "r2" in text
        has_r3 = "r3" in text
        has_r4 = "r4" in text

        has_25 = "25%" in text
        has_50 = "50%" in text

        # crop 50%
        if has_r4 and has_50 and not (has_r1 or has_r2 or has_r3):
            return "Oasis crop 50%"

        # wood 50%
        if has_r1 and has_50 and not (has_r2 or has_r3 or has_r4):
            return "Oasis wood 50%"
        
        # clay 50%
        if has_r2 and has_50 and not (has_r1 or has_r3 or has_r4):
            return "Oasis clay 50%"
        
        # iron 50%
        if has_r3 and has_50 and not (has_r1 or has_r2 or has_r4):
            return "Oasis iron 50%"

        # двойные бонусы 25% + 25%
        if has_r1 and has_r4 and has_25:
            return "Oasis wood 25% crop 25%"

        if has_r2 and has_r4 and has_25:
            return "Oasis clay 25% crop 25%"

        if has_r3 and has_r4 and has_25:
            return "Oasis iron 25% crop 25%"

        # одиночные бонусы 25%
        if has_r1 and has_25:
            return "Oasis wood 25%"

        if has_r2 and has_25:
            return "Oasis clay 25%"

        if has_r3 and has_25:
            return "Oasis iron 25%"

        if has_r4 and has_25:
            return "Oasis crop 25%"

        # если формат неизвестен
        logger.warning(f"Unknown oasis format: {text}")

        return "Unknown oasis"
    
    async def save_tiles_to_db(self, batch: TilesBatch, server_id: int) -> Dict[str, Any]:
        """
        Сохраняет данные тайлов в БД (таблица maps).
        Аргументы:
            batch: Бач данных тайлов для сохранения
            server_id: ID сервера в БД
        Возвращает:
            Словарь с информацией о сохранённых данных
        """
        from sqlalchemy import select, insert
        from sqlalchemy.dialects.sqlite import insert
        from app.game.models import MapCell, TypeField
        
        logger.info("Начинаем сохранять в БД")

        async with async_session_maker() as session:
            # Получаем все типы полей из БД
            result = await session.execute(select(TypeField))
            type_fields = {tf.name: tf.id for tf in result.scalars().all()}
            
            # Подготавливаем данные для вставки
            cells_data = []
            skipped_tiles = 0

            for tile in batch.tiles:
                type_name = self._determine_field_type_name(tile.title, tile.text)

                # пропускаем неизвестные типы
                if not type_name:
                    skipped_tiles += 1
                    logger.debug(
                        f"Skip tile ({tile.position.x}, {tile.position.y}) "
                        f"title={tile.title}"
                    )
                    continue

                type_id = type_fields.get(type_name)

                # если тип не найден в справочнике — тоже пропускаем
                if type_id is None:
                    skipped_tiles += 1
                    logger.warning(
                        f"Тип поля '{type_name}' не найден в type_fields. "
                        f"Tile skipped: ({tile.position.x}, {tile.position.y})"
                    )
                    continue

                cells_data.append({
                    "server_id": server_id,
                    "x": tile.position.x,
                    "y": tile.position.y,
                    "type_id": type_id
                })
            
            # logger.info(cells_data)

            stmt = insert(MapCell).values(cells_data)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["server_id", "x", "y"]
            )

            # await session.execute(stmt)
            try:
                result = await session.execute(stmt)
                inserted_count = result.rowcount
                logger.info(f"Вставлено строк: {inserted_count}")
                
                if inserted_count > 0:
                    await session.commit()  # Явный commit
                    logger.info("Транзакция закоммичена")
                else:
                    logger.warning("Ничего не вставлено")
                    
            except Exception as e:
                logger.error(f"Ошибка вставки: {e}")
                raise
            
            logger.info(f"Сохранены данные карты для сервера {server_id}.")
            logger.info(f"Подготовлено: {len(cells_data)}, пропущено: {skipped_tiles}")

            return {
                "server_id": server_id,
                "tiles_count": len(cells_data)
            }
        
        logger.info("Закончили сохранять в БД")  


# Экземпляр сервиса для использования в роутерах
map_upload_service = MapUploadService()

"""
Потоковый SQL-парсер для файлов Travian map.sql.

Этот парсер читает большие SQL-файлы построчно, не загружая весь файл в память.
Он извлекает INSERT-выражения и парсит значения в словари.
"""
import re
import asyncio
import aiohttp
import time
import os
from typing import AsyncIterator, Optional
from datetime import datetime
from loguru import logger


# Директория для сохранения файлов карты
MAP_HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'map_history')


class MapParser:
    """
    Потоковый парсер для файлов Travian map.sql.
    
    Поддерживает парсинг:
    - INSERT INTO 'npc' statements (деревни)
    - Данные игроков и альянсов, встроенные в записи деревень
    """
    
    # Регулярные выражения для парсинга SQL
    INSERT_PATTERN = re.compile(
        r"INSERT INTO\s+[`'](?P<table>\w+)[`']\s+"
        r"VALUES\s*\((?P<values>.+)\)",
        re.IGNORECASE
    )
    
    # Шаблон для поиска координат и данных деревни
    VILLAGE_PATTERN = re.compile(
        r"\(?\s*'(\d+)'\s*,\s*'(\d+)'\s*,\s*'(\d+)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'(\d+)'\s*,\s*'(\d+)'\s*\)?",
        re.IGNORECASE
    )
    
    def __init__(self, batch_size: int = 1000):
        """
        Инициализация парсера.
        
        Параметры:
            batch_size: Количество записей для возврата за одну партию
        """
        self.batch_size = batch_size
        self._buffer: list[dict] = []
        
    async def parse_url(self, url: str, timeout: int = 300) -> AsyncIterator[list[dict]]:
        """
        Загрузка и парсинг map.sql по URL.
        Параметры:
            url: URL для загрузки map.sql
            timeout: Таймаут загрузки в секундах
        Возвращает:
            Партии проанализированных записей деревень в виде словарей
        """
        logger.info(f"Starting download from URL: {url}")
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            logger.debug(f"Created session with timeout: {timeout}s")
            
            async with session.get(url) as response:
                logger.info(f"Connected to {url}, status: {response.status}")
                
                if response.status != 200:
                    logger.error(f"HTTP error {response.status} for URL: {url}")
                    
                response.raise_for_status()
                
                # Получить размер контента, если доступно
                content_length = response.headers.get('content-length')
                if content_length:
                    logger.info(f"Total file size: {int(content_length) / 1024 / 1024:.2f} MB")
                
                # Потоковая передача контента построчно
                line_count = 0
                record_count = 0
                start_time = time.time()
                last_log_time = start_time
                
                logger.info("Starting to stream and parse file content...")
                
                async for line in response.content:
                    line_count += 1
                    
                    try:
                        decoded_line = line.decode('utf-8', errors='ignore').strip()
                        if decoded_line:
                            records = self._parse_line(decoded_line)
                            if records:
                                record_count += len(records)
                                self._buffer.extend(records)
                                
                                # Логировать прогресс каждые 1000 строк или каждые 5 секунд
                                current_time = time.time()
                                if line_count % 1000 == 0 or current_time - last_log_time > 5:
                                    elapsed = current_time - start_time
                                    rate = record_count / elapsed if elapsed > 0 else 0
                                    logger.debug(f"Processed {line_count} lines, "
                                            f"found {record_count} records, "
                                            f"speed: {rate:.1f} records/sec")
                                    last_log_time = current_time
                                
                                if len(self._buffer) >= self.batch_size:
                                    logger.debug(f"Yielding batch of {len(self._buffer)} records")
                                    yield self._buffer
                                    self._buffer = []
                    except Exception as e:
                        logger.warning(f"Error parsing line {line_count}: {e}")
                        continue
                        
            logger.info(f"Finished streaming. Total lines: {line_count}, Total records: {record_count}")
                        
        # Yield remaining buffer
        if self._buffer:
            logger.info(f"Yielding final batch of {len(self._buffer)} records")
            yield self._buffer
            self._buffer = []
            
        elapsed = time.time() - start_time
        logger.info(f"Parsing completed in {elapsed:.2f} seconds. "
                    f"Average speed: {record_count/elapsed:.1f} records/sec")
            
    async def parse_file(self, file_path: str) -> AsyncIterator[list[dict]]:
        """
        Парсинг map.sql из локального файла с подробным логированием.
        Параметры:
            file_path: Путь к локальному файлу map.sql
        Возвращает:
            Партии проанализированных записей деревень в виде словарей
        """
        logger.info(f"="*50)
        logger.info(f"НАЧАЛО ПАРСИНГА ФАЙЛА: {file_path}")
        logger.info(f"="*50)
        
        # Проверяем существование файла
        if not os.path.exists(file_path):
            logger.error(f"ФАЙЛ НЕ НАЙДЕН: {file_path}")
            return
        
        # Получаем размер файла
        file_size = os.path.getsize(file_path)
        logger.info(f"Размер файла: {file_size / (1024*1024):.2f} MB")
        
        line_count = 0
        insert_count = 0
        village_records_count = 0
        start_time = time.time()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                logger.info("Файл успешно открыт, начинаем построчное чтение...")
                
                for line in f:
                    line_count += 1
                    
                    # Логируем каждую 1000-ю строку для отслеживания прогресса
                    if line_count % 10000 == 0:
                        elapsed = time.time() - start_time
                        logger.info(f"Прогресс: обработано {line_count} строк, "
                                f"найдено INSERT: {insert_count}, "
                                f"записей деревень: {village_records_count}, "
                                f"время: {elapsed:.1f}с")
                    
                    try:
                        stripped = line.strip()
                        if not stripped:
                            continue  # пропускаем пустые строки
                        
                        # Логируем первые несколько строк для отладки
                        # if line_count <= 20:
                            # logger.debug(f"Строка {line_count}: {stripped[:200]}")
                        
                        # Проверяем, содержит ли строка INSERT
                        if 'INSERT' in stripped.upper():
                            insert_count += 1
                            
                            # Детальное логирование первых INSERT запросов
                            # if insert_count <= 10:
                                # logger.debug(f"НАЙДЕН INSERT #{insert_count} в строке {line_count}")
                                # logger.debug(f"  Текст: {stripped[:300]}")
                        
                        records = self._parse_line(stripped)
                        
                        if records:
                            village_records_count += len(records)
                            
                            # Логируем первые найденные записи
                            if village_records_count <= len(records) * 5:  # примерно первые 5 записей
                                for i, record in enumerate(records[:3]):  # первые 3 из каждой партии
                                    logger.debug(f"  -> Найдена запись деревни #{village_records_count - len(records) + i + 1}: "
                                            f"ID={record.get('village_id')}, "
                                            f"Название='{record.get('village_name')}', "
                                            f"Игрок='{record.get('player_name')}'")
                            
                            self._buffer.extend(records)
                            
                            if len(self._buffer) >= self.batch_size:
                                logger.info(f"Набрана партия из {len(self._buffer)} записей, отправляем...")
                                yield self._buffer
                                self._buffer = []
                                
                    except Exception as e:
                        logger.warning(f"Ошибка при обработке строки {line_count}: {e}")
                        logger.debug(f"Проблемная строка: {stripped[:200]}")
                        continue
                        
        except Exception as e:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при чтении файла: {e}")
            raise
        
        # Yield remaining buffer
        if self._buffer:
            logger.info(f"Отправляем остаток из {len(self._buffer)} записей")
            yield self._buffer
            self._buffer = []
    
        # Итоговая статистика
        elapsed = time.time() - start_time
        logger.info(f"="*50)
        logger.info(f"ПАРСИНГ ЗАВЕРШЕН")
        logger.info(f"Всего обработано строк: {line_count}")
        logger.info(f"Найдено INSERT запросов: {insert_count}")
        logger.info(f"Извлечено записей деревень: {village_records_count}")
        logger.info(f"Затраченное время: {elapsed:.2f} секунд")
        logger.info(f"Скорость обработки: {line_count/elapsed:.1f} строк/сек")
        logger.info(f"="*50)
            
    def _parse_line(self, line: str) -> list[dict]:
        """
        Парсинг одной строки SQL с расширенным логированием.
        """
        records = []
        
        # Быстрая проверка - если нет INSERT, даже не пытаемся парсить
        if 'INSERT' not in line.upper():
            return records
        
        # Попытка соответствия INSERT-выражениям
        match = self.INSERT_PATTERN.search(line)
        if not match:
            # Строка содержит INSERT, но не подходит под паттерн
            # Возможно, другой формат SQL
            logger.debug(f"INSERT не соответствует паттерну: {line[:100]}")
            return records
            
        # table = match.group('table').lower()
        # values_str = match.group('values')
        values_str = line.split("VALUES", 1)[1].strip()
        # logger.debug(f"Найден INSERT, длина значений: {len(values_str)}")
        
        
        # Попытка парсинга данных деревни
        # village_records = self._parse_village_values(values_str)
        # if village_records:
        #     logger.debug(f"  Извлечено {len(village_records)} записей деревень из INSERT")
        # else:
        #     logger.debug(f"  Не удалось извлечь записи из VALUES: {values_str[:200]}")
        # records.extend(village_records)

        all_records = self._parse_all_values(values_str)
        # if all_records:
        #     logger.debug(f"  Извлечено {len(all_records)} записей из INSERT")
        # else:
        #     logger.debug(f"  Не удалось извлечь записи из VALUES: {values_str[:200]}")
        records.extend(all_records)

            
        return records
        
    def _parse_village_values(self, values_str: str) -> list[dict]:
        """
        Парсинг значений INSERT для деревни с логированием проблем.
        """
        records = []
        
        # Проверяем, есть ли вообще какие-то значения
        if not values_str or len(values_str) < 10:
            logger.debug(f"Слишком короткая строка VALUES: {values_str}")
            return records
        
        # Пробуем первый паттерн
        pattern1 = re.compile(
            r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
            re.IGNORECASE
        )
        
        matches = list(pattern1.finditer(values_str))
        if not matches:
            # Если первый паттерн не сработал, пробуем альтернативный формат
            # Например, без кавычек вокруг чисел или другой порядок полей
            logger.debug(f"Паттерн 1 не дал совпадений. Пробуем альтернативный формат...")
            
            # Альтернативный паттерн - более гибкий
            pattern2 = re.compile(
                r"\(\s*'?(\d+)'?\s*,\s*'?(\d+)'?\s*,\s*'?(\d+)'?\s*,"  # x, y, id могут быть в кавычках или нет
                r"\s*'([^']*)'\s*,\s*'([^']*)'\s*,"                    # name, player
                r"\s*'([^']*)'\s*,\s*'([^']*)'\s*,"                    # alliance_tag, alliance_name
                r"\s*'?(\d+)'?\s*,\s*'?(\d+)'?\s*\)",                  # race, pop могут быть в кавычках
                re.IGNORECASE
            )
            matches = list(pattern2.finditer(values_str))
            
            if not matches:
                # Если и это не сработало, логируем структуру для анализа
                logger.debug(f"НЕ УДАЛОСЬ НАЙТИ СОВПАДЕНИЯ В VALUES")
                logger.debug(f"Образец VALUES (первые 200 символов): {values_str[:200]}")
                
                # Пробуем определить структуру вручную
                parts = values_str.split(',')
                logger.debug(f"Строка разбита на {len(parts)} частей")
                for i, part in enumerate(parts[:10]):  # первые 10 частей
                    logger.debug(f"  Часть {i}: {part[:50]}")
        
        # Обрабатываем найденные совпадения
        for match_num, match in enumerate(matches):
            try:
                # Логируем группы для первого совпадения
                if match_num == 0:
                    logger.debug(f"Найдено совпадение. Группы:")
                    for i in range(1, 10):  # группы с 1 по 9
                        try:
                            logger.debug(f"  Группа {i}: '{match.group(i)}'")
                        except IndexError:
                            pass
                
                x = int(match.group(1))
                y = int(match.group(2))
                village_id = int(match.group(3))
                village_name = match.group(4) or None
                player_name = match.group(5) if match.group(5) else None
                alliance_tag = match.group(6) if match.group(6) else None
                alliance_name = match.group(7) if match.group(7) else None
                race = int(match.group(8)) if match.group(8) else None
                population = int(match.group(9)) if match.group(9) else 0
                
                # Вычисление map_id из координат (стандартная формула Travian)
                map_id = (x + 401) * 801 + (y + 401)
                
                records.append({
                    'x': x,
                    'y': y,
                    'village_id': village_id,
                    'village_name': village_name,
                    'player_name': player_name,
                    'alliance_tag': alliance_tag,
                    'alliance_name': alliance_name,
                    'race_id': race,
                    'population': population,
                    'map_id': map_id,
                })
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Ошибка при извлечении данных из совпадения {match_num}: {e}")
                continue
        
        # if records:
        #     logger.debug(f"Успешно извлечено {len(records)} записей")
        # else:
        #     logger.debug(f"Не удалось извлечь записи из VALUES")
            
        return records

    def parse_sql_values(self, values_str: str):
        rows = []
        row = []
        value = []
        
        in_string = False
        escape = False
        
        for ch in values_str:
            if in_string:
                if escape:
                    value.append(ch)
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "'":
                    in_string = False
                else:
                    value.append(ch)
                continue
            
            if ch == "'":
                in_string = True
                continue
            
            if ch == "(":
                row = []
                value = []
                continue
            
            if ch == ",":
                v = "".join(value).strip()
                row.append(v)
                value = []
                continue
            
            if ch == ")":
                v = "".join(value).strip()
                row.append(v)
                rows.append(row)
                value = []
                continue
            
            value.append(ch)
    
        return rows
    
    def _parse_all_values(self, values_str: str) -> list[dict]:
        """
        Парсинг значений INSERT для деревни.
        Формат: (map_id, x, y, race_id, village_id, village_name, player_id, player_name, 
                alliance_id, alliance_tag, total_population, ...)
        """
        
        values = self.parse_sql_values(values_str)

        records = []

        for r in values:
            records.append({
                "map_id": int(r[0]),
                "x": int(r[1]),
                "y": int(r[2]),
                "race_id": int(r[3]),
                "village_id": int(r[4]),
                "village_name": r[5] or None,
                "account_id": int(r[6]),
                "player_name": r[7] or None,
                "alliance_id": int(r[8]) if r[8] != "0" else None,
                "alliance_tag": r[9] or None,
                "population": int(r[10]),
            })
        
        # records = []
        
        # # Регулярное выражение для извлечения 11 полей
        # pattern = re.compile(
        #     r"^\s*(\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*,"  # убрали \(
        #     r"\s*(\d+)\s*,"                                            # village_id
        #     r"\s*'([^']*)'\s*,"                                        # village_name
        #     r"\s*(\d+)\s*,"                                            # player_id
        #     r"\s*'([^']*)'\s*,"                                        # player_name
        #     r"\s*(\d+)\s*,"                                            # alliance_id
        #     r"\s*'([^']*)'\s*,"                                        # alliance_tag
        #     r"\s*(\d+)\s*,",                                           # total_population
        #     re.IGNORECASE
        # )
        
        # for match in pattern.finditer(values_str):
        #     try:
        #         map_id = int(match.group(1))
        #         x = int(match.group(2))
        #         y = int(match.group(3))
        #         race_id = int(match.group(4))
        #         village_id = int(match.group(5))
        #         village_name = match.group(6).strip() if match.group(6) else None
        #         player_id = int(match.group(7))
        #         player_name = match.group(8).strip() if match.group(8) else None
        #         alliance_id = int(match.group(9)) if match.group(9) != '0' else None
        #         alliance_tag = match.group(10).strip() if match.group(10) else None
        #         total_population = int(match.group(11))
                
        #         records.append({
        #             'map_id': map_id,                    # mapId деревни
        #             'x': x,                               # x координата
        #             'y': y,                               # y координата
        #             'race_id': race_id,                   # id расы
        #             'village_id': village_id,             # id деревни
        #             'village_name': village_name,         # название деревни
        #             'player_id': player_id,               # id игрока
        #             'player_name': player_name,           # имя игрока
        #             'alliance_id': alliance_id,           # id альянса
        #             'alliance_tag': alliance_tag,         # тег альянса
        #             'population': total_population,       # население всех деревень игрока
        #         })
                
        #         # Логируем первую успешную запись для проверки
        #         if len(records) == 1:
        #             logger.debug(f"ПЕРВАЯ УСПЕШНАЯ ЗАПИСЬ: {records[0]}")
                    
        #     except (ValueError, IndexError) as e:
        #         logger.debug(f"Ошибка парсинга: {e}")
        #         continue
        
        if not records:
            logger.debug(f"Не удалось извлечь записи из: {values_str[:200]}")
            
        return records


def generate_map_filename(server_url: str) -> str:
    """
    Генерирует имя файла для сохранения map.sql на основе URL сервера.
    
    Формат: YYYYMMDD_HHMMSS_server_url.sql.txt
    Пример: 20260307_151340_ts19.travian.com.sql.txt
    
    Параметры:
        server_url: URL сервера (например, https://ts19.travian.com)
        
    Возвращает:
        Сгенерированное имя файла
    """
    # Удалить протокол и слеши
    clean_url = server_url.replace('https://', '').replace('http://', '').rstrip('/')
    # Заменить недопустимые символы в имени файла
    clean_url = clean_url.replace('.', '_').replace(':', '_').replace('/', '_')
    
    # Формат даты и времени
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    
    return f"{timestamp}_{clean_url}.sql.txt"

async def download_and_save_map_file(url: str) -> AsyncIterator[list[dict]]:
    """
    Загружает файл map.sql по URL и сохраняет его в указанную директорию.
    
    Параметры:
        url: URL для загрузки map.sql
        save_dir: Директория для сохранения файла. Если None - используется MAP_HISTORY_DIR
        
    Возвращает:
        Кортеж (путь к сохраненному файлу, список проанализированных записей)
    """
    save_dir = MAP_HISTORY_DIR
    
    # Создать директорию если не существует
    os.makedirs(save_dir, exist_ok=True)
    
    # Извлечь server_url из URL для генерации имени файла
    # URL имеет вид https://server/map.sql или https://server/database/map.sql  ???
    from urllib.parse import urlparse
    parsed = urlparse(url)
    server_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Сгенерировать имя файла
    filename = generate_map_filename(server_url)
    filepath = os.path.join(save_dir, filename)
    
    logger.info(f"Downloading map file from {url} to {filepath}")
    
    timeout_obj = aiohttp.ClientTimeout(total=300)
    
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            
            # Сохранять файл построчно
            with open(filepath, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
    
    logger.info(f"Map file saved to {filepath}")
    
    # Парсить сохраненный файл
    parser = MapParser(batch_size=1000) # ???
    async for batch in parser.parse_file(filepath):
        yield batch

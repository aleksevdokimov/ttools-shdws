import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger


class AttackLogger:
    """Логирует данные об атаках в файл."""

    def __init__(self, filename: str = "attacks_log.json"):
        self.filename = filename
        self.records = self._load_records()

    def _load_records(self) -> List[Dict]:
        """Загрузить историю записей."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading attack records: {e}")
                return []
        return []

    def _save_records(self):
        """Сохранить записи в файл."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Error saving attack records: {e}")

    def log_attack_data(self, data: Dict[str, Any], headers: Dict[str, str], raw_body: str):
        """Добавить запись о данных атак."""
        from app.utils.code_generator import decode_player_name

        player_name = decode_player_name(headers.get("x-player-name", ""))

        record = {
            "id": str(uuid.uuid4()),
            "received_at": datetime.now().isoformat(),
            "player_name": player_name,
            "server": headers.get("x-server", ""),
            "auth_key": headers.get("x-auth-key", "")[:8] + "..." if headers.get("x-auth-key") else "",
            "type": data.get("type", "unknown"),
            "data_count": len(data.get("data", [])),
            "raw_body": raw_body[:1000] if raw_body else "",  # Ограничиваем размер
            "metadata": data.get("metadata", {})
        }

        # Ограничиваем количество хранимых записей
        if len(self.records) > 1000:
            self.records = self.records[-900:]

        self.records.append(record)
        self._save_records()
        logger.info(f"Attack data logged from {player_name} with {record['data_count']} items")

    def get_recent_records(self, limit: int = 50) -> List[Dict]:
        """Получить последние записи."""
        return self.records[-limit:] if self.records else []


class RallyPointLogger:
    """Логирует данные из пункта сбора в файл."""

    def __init__(self, filename: str = "rally_point_log.json"):
        self.filename = filename
        self.records = self._load_records()

    def _load_records(self) -> List[Dict]:
        """Загрузить историю записей."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading rally point records: {e}")
                return []
        return []

    def _save_records(self):
        """Сохранить записи в файл."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Error saving rally point records: {e}")

    def log_rally_data(self, data: Dict[str, Any], headers: Dict[str, str], raw_body: str):
        """Добавить запись о данных из пункта сбора."""
        from app.utils.code_generator import decode_player_name

        player_name = decode_player_name(headers.get("x-player-name", ""))

        movements = data.get("movement_info", [])
        record = {
            "id": str(uuid.uuid4()),
            "received_at": datetime.now().isoformat(),
            "player_name": player_name,
            "server": headers.get("x-server", ""),
            "auth_key": headers.get("x-auth-key", "")[:8] + "..." if headers.get("x-auth-key") else "",
            "movements_count": len(movements),
            "raw_body": raw_body[:2000] if raw_body else "",  # Ограничиваем размер
            "movements": movements[:50] if movements else [],  # Сохраняем первые 50 движений
            "metadata": data.get("metadata", {})
        }

        if len(self.records) > 1000:
            self.records = self.records[-900:]

        self.records.append(record)
        self._save_records()
        logger.info(f"Rally point data logged from {player_name} with {record['movements_count']} movements")

    def get_recent_records(self, limit: int = 50) -> List[Dict]:
        """Получить последние записи."""
        return self.records[-limit:] if self.records else []


# Глобальные экземпляры
attack_logger = AttackLogger()
rally_point_logger = RallyPointLogger()
import os
from typing import Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DB_URL: str = f"sqlite+aiosqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))}/data/db.sqlite3"
    SECRET_KEY: str = "default_dev_secret_change_in_production"
    ALGORITHM: str = "HS256"
    SITE_NAME: str = "TTools Shadows"
    # Режим отладки - для localhost делаем False, для production - True
    DEBUG: Union[bool, str] = False
    # Настройки scheduler
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_UPDATE_INTERVAL_HOURS: int = 5
    
    @field_validator('DEBUG', mode='before')
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return False

    model_config = SettingsConfigDict(env_file=".env")


# Получаем параметры для загрузки переменных среды
settings = Settings()
database_url = settings.DB_URL

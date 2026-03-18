from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# === Server Schemas ===

class ServerBase(BaseModel):
    """Базовая схема сервера."""
    name: str = Field(..., min_length=1, max_length=100, description="Название сервера")
    url: str = Field(..., max_length=255, description="URL сервера")
    info: Optional[str] = Field(None, description="Описание сервера")
    settings: dict = Field(
        default={"server_time": "UTC+1", "speed": "x1", "server_type": "Classic", "Size": "400"},
        description="Настройки сервера"
    )
    update_time: Optional[datetime] = Field(None, description="Время обновления")
    is_active: bool = Field(True, description="Статус активности")
    last_update_info: Optional[datetime] = Field(None, description="Время последнего успешного обновления")


class ServerCreate(ServerBase):
    """Схема создания сервера."""
    pass


class ServerUpdate(BaseModel):
    """Схема обновления сервера."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, max_length=255)
    info: Optional[str] = None
    settings: Optional[dict] = None
    update_time: Optional[datetime] = None
    is_active: Optional[bool] = None


class ServerResponse(ServerBase):
    """Схема ответа сервера."""
    id: int = Field(..., description="ID сервера")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    deleted_at: Optional[datetime] = Field(None, description="Дата удаления")
    last_update_info: Optional[datetime] = Field(None, description="Дата последнего обновления карты")
    model_config = ConfigDict(from_attributes=True)


# === Race Schemas ===

class RaceBase(BaseModel):
    """Базовая схема расы."""
    name: str = Field(..., min_length=1, max_length=50, description="Название расы")


class RaceCreate(RaceBase):
    """Схема создания расы."""
    pass


class RaceUpdate(BaseModel):
    """Схема обновления расы."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)


class RaceResponse(RaceBase):
    """Схема ответа расы."""
    id: int = Field(..., description="ID расы")
    deleted_at: Optional[datetime] = Field(None, description="Дата удаления")
    
    model_config = ConfigDict(from_attributes=True)


# === Alliance Schemas ===

class AllianceBase(BaseModel):
    """Базовая схема альянса."""
    server_id: int = Field(..., description="ID сервера")
    alliance_id: Optional[int] = Field(None, description="ID из игры")
    tag: Optional[str] = Field(None, max_length=20, description="Тег альянса")
    name: Optional[str] = Field(None, max_length=255, description="Название альянса")
    info: Optional[str] = Field(None, description="Описание альянса")


class AllianceCreate(AllianceBase):
    """Схема создания альянса."""
    pass


class AllianceUpdate(BaseModel):
    """Схема обновления альянса."""
    server_id: Optional[int] = None
    alliance_id: Optional[int] = None
    tag: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=255)
    info: Optional[str] = None


class AllianceResponse(AllianceBase):
    """Схема ответа альянса."""
    id: int = Field(..., description="ID альянса")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    deleted_at: Optional[datetime] = Field(None, description="Дата удаления")
    
    model_config = ConfigDict(from_attributes=True)


# === Player Schemas ===

class PlayerBase(BaseModel):
    """Базовая схема игрока."""
    server_id: int = Field(..., description="ID сервера")
    user_id: Optional[int] = Field(None, description="ID пользователя системы")
    account_id: Optional[int] = Field(None, description="ID из игры")
    name: str = Field(..., min_length=1, max_length=255, description="Имя игрока")
    alliance_id: Optional[int] = Field(None, description="ID альянса")
    population: int = Field(0, ge=0, description="Население")
    race_id: Optional[int] = Field(None, description="ID расы")
    info: Optional[str] = Field(None, description="Информация об игроке")
    is_verified: bool = Field(False, description="Верифицирован")


class PlayerCreate(PlayerBase):
    """Схема создания игрока."""
    pass


class PlayerUpdate(BaseModel):
    """Схема обновления игрока."""
    server_id: Optional[int] = None
    user_id: Optional[int] = None
    account_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    alliance_id: Optional[int] = None
    population: Optional[int] = Field(None, ge=0)
    race_id: Optional[int] = None
    info: Optional[str] = None
    is_verified: Optional[bool] = None


class PlayerResponse(PlayerBase):
    """Схема ответа игрока."""
    id: int = Field(..., description="ID игрока")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    deleted_at: Optional[datetime] = Field(None, description="Дата удаления")
    
    model_config = ConfigDict(from_attributes=True)


# === Village Schemas ===

class VillageBase(BaseModel):
    """Базовая схема деревни."""
    server_id: int = Field(..., description="ID сервера")
    map_id: Optional[int] = Field(None, description="ID на карте")
    village_id: Optional[int] = Field(None, description="ID из игры")
    name: Optional[str] = Field(None, max_length=255, description="Название деревни")
    x: Optional[int] = Field(None, description="X координата")
    y: Optional[int] = Field(None, description="Y координата")
    player_id: Optional[int] = Field(None, description="ID владельца")
    race_id: Optional[int] = Field(None, description="ID расы")
    village_type: Optional[str] = Field(None, max_length=50, description="Тип деревни")
    info: Optional[str] = Field(None, description="Информация о деревне")


class VillageCreate(VillageBase):
    """Схема создания деревни."""
    pass


class VillageUpdate(BaseModel):
    """Схема обновления деревни."""
    server_id: Optional[int] = None
    map_id: Optional[int] = None
    village_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)
    x: Optional[int] = None
    y: Optional[int] = None
    player_id: Optional[int] = None
    race_id: Optional[int] = None
    village_type: Optional[str] = Field(None, max_length=50)
    info: Optional[str] = None


class VillageResponse(VillageBase):
    """Схема ответа деревни."""
    id: int = Field(..., description="ID деревни")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    deleted_at: Optional[datetime] = Field(None, description="Дата удаления")
    
    model_config = ConfigDict(from_attributes=True)


# === Attack Schemas ===

class AttackBase(BaseModel):
    """Базовая схема атаки."""
    server_id: int = Field(..., description="ID сервера")
    attacker_player_id: Optional[int] = Field(None, description="ID атакующего игрока")
    target_village_id: Optional[int] = Field(None, description="ID целевой деревни")
    defender_player_id: Optional[int] = Field(None, description="ID защищающегося игрока")
    alliance_id: Optional[int] = Field(None, description="ID альянса")
    arrival_time: datetime = Field(..., description="Время прибытия")
    attack_type: Optional[str] = Field(None, max_length=50, description="Тип атаки (raid/attack/siege)")
    wave_group: Optional[int] = Field(None, description="Группа волн")
    is_processed: bool = Field(False, description="Обработана")


class AttackCreate(AttackBase):
    """Схема создания атаки."""
    pass


class AttackUpdate(BaseModel):
    """Схема обновления атаки."""
    server_id: Optional[int] = None
    attacker_player_id: Optional[int] = None
    target_village_id: Optional[int] = None
    defender_player_id: Optional[int] = None
    alliance_id: Optional[int] = None
    arrival_time: Optional[datetime] = None
    attack_type: Optional[str] = Field(None, max_length=50)
    wave_group: Optional[int] = None
    is_processed: Optional[bool] = None


class AttackResponse(AttackBase):
    """Схема ответа атаки."""
    id: int = Field(..., description="ID атаки")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    deleted_at: Optional[datetime] = Field(None, description="Дата удаления")
    
    model_config = ConfigDict(from_attributes=True)


# === ApiKey Schemas ===

class ApiKeyBase(BaseModel):
    """Базовая схема API ключа."""
    player_id: int = Field(..., description="ID игрока")
    server_id: int = Field(..., description="ID сервера")
    expires_at: Optional[datetime] = Field(None, description="Срок действия")


class ApiKeyCreate(ApiKeyBase):
    """Схема создания API ключа."""
    pass


class ApiKeyResponse(ApiKeyBase):
    """Схема ответа API ключа."""
    id: int = Field(..., description="ID ключа")
    key_value: str = Field(..., description="Значение ключа")
    is_active: bool = Field(..., description="Статус активности")
    created_at: datetime = Field(..., description="Дата создания")
    
    model_config = ConfigDict(from_attributes=True)


# === UserSettings Schemas ===

class UserSettingsBase(BaseModel):
    """Базовая схема настроек пользователя."""
    user_id: int = Field(..., description="ID пользователя")
    settings: dict = Field(default={}, description="Настройки")


class UserSettingsCreate(UserSettingsBase):
    """Схема создания настроек."""
    pass


class UserSettingsUpdate(BaseModel):
    """Схема обновления настроек."""
    settings: Optional[dict] = None


class UserSettingsResponse(UserSettingsBase):
    """Схема ответа настроек."""
    id: int = Field(..., description="ID настроек")
    
    model_config = ConfigDict(from_attributes=True)


# === UserServer Schemas ===

class UserServerBase(BaseModel):
    """Базовая схема связи пользователя с сервером."""
    user_id: int = Field(..., description="ID пользователя")
    server_id: int = Field(..., description="ID сервера")
    is_active: bool = Field(False, description="Статус активности")


class UserServerCreate(UserServerBase):
    """Схема создания связи."""
    pass


class UserServerUpdate(BaseModel):
    """Схема обновления связи."""
    is_active: Optional[bool] = None


class UserServerResponse(UserServerBase):
    """Схема ответа связи."""
    id: int = Field(..., description="ID связи")
    created_at: datetime = Field(..., description="Дата создания")
    
    model_config = ConfigDict(from_attributes=True)


# === Map Update Schemas ===

class MapUpdateResponse(BaseModel):
    """Схема ответа статуса обновления карты."""
    id: int = Field(..., description="ID записи обновления")
    server_id: int = Field(..., description="ID сервера")
    started_at: datetime = Field(..., description="Время начала")
    finished_at: Optional[datetime] = Field(None, description="Время окончания")
    status: str = Field(..., description="Статус: running, completed, failed")
    villages_processed: int = Field(0, description="Обработано деревень")
    players_processed: int = Field(0, description="Обработано игроков")
    alliances_processed: int = Field(0, description="Обработано альянсов")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    duration_ms: Optional[int] = Field(None, description="Длительность в мс")
    
    model_config = ConfigDict(from_attributes=True)


class MapUpdateRequest(BaseModel):
    """Схема запроса на обновление карты."""
    map_url: Optional[str] = Field(None, description="URL к map.sql (опционально)")


class ServerUpdateResponse(BaseModel):
    """Схема ответа на запрос обновления сервера."""
    status: str = Field(..., description="Статус: success, error, skipped")
    server_id: int = Field(..., description="ID сервера")
    server_name: Optional[str] = Field(None, description="Название сервера")
    stats: Optional[dict] = Field(None, description="Статистика обновления")
    error: Optional[str] = Field(None, description="Ошибка")
    reason: Optional[str] = Field(None, description="Причина (если skipped)")
    last_update_info: Optional[datetime] = Field(None, description="Время последнего успешного обновления")


class UpdateAllResponse(BaseModel):
    """Схема ответа на запрос обновления всех серверов."""
    total: int = Field(..., description="Всего серверов")
    success: int = Field(..., description="Успешно обновлено")
    failed: int = Field(..., description="Не удалось обновить")
    skipped: int = Field(..., description="Пропущено")
    results: List[ServerUpdateResponse] = Field(..., description="Результаты по каждому серверу")


# === Map Tile Upload Schemas ===

class TilePosition(BaseModel):
    """Схема позиции тайла на карте."""
    x: int = Field(..., description="X координата")
    y: int = Field(..., description="Y координата")


class Tile(BaseModel):
    """Схема тайла карты."""
    position: TilePosition = Field(..., description="Позиция тайла")
    text: Optional[str] = Field(None, description="Текст тайла")
    title: Optional[str] = Field(None, description="Заголовок тайла")
    aid: Optional[int] = Field(None, description="ID альянса")
    did: Optional[int] = Field(None, description="ID деревни")
    uid: Optional[int] = Field(None, description="ID игрока")


class TilesBatch(BaseModel):
    """Схема батча тайлов для загрузки."""
    server: str = Field(..., description="URL сервера")
    tiles: List[Tile] = Field(..., description="Список тайлов")


class TilesUploadResponse(BaseModel):
    """Схема ответа на загрузку тайлов."""
    status: str = Field(..., description="Статус: ok, error")
    tiles_count: int = Field(..., description="Количество сохранённых тайлов")
    filename: Optional[str] = Field(None, description="Имя сохранённого файла")


# === TypeField Schemas ===

class TypeFieldBase(BaseModel):
    """Базовая схема типа поля карты."""
    name: str = Field(..., max_length=100, description="Название типа поля")
    wood_fields: Optional[int] = Field(None, description="Уровень леса")
    clay_fields: Optional[int] = Field(None, description="Уровень глины")
    iron_fields: Optional[int] = Field(None, description="Уровень железа")
    crop_fields: Optional[int] = Field(None, description="Уровень зерна")
    wood_bonus: Optional[int] = Field(None, description="Бонус леса (%)")
    clay_bonus: Optional[int] = Field(None, description="Бонус глины (%)")
    iron_bonus: Optional[int] = Field(None, description="Бонус железа (%)")
    crop_bonus: Optional[int] = Field(None, description="Бонус зерна (%)")
    can_be_settled: bool = Field(False, description="Можно ли построить деревню")
    can_be_attacked: bool = Field(False, description="Можно ли атаковать")


class TypeFieldCreate(TypeFieldBase):
    """Схема создания типа поля."""
    pass


class TypeFieldUpdate(BaseModel):
    """Схема обновления типа поля."""
    name: Optional[str] = Field(None, max_length=100)
    wood_fields: Optional[int] = None
    clay_fields: Optional[int] = None
    iron_fields: Optional[int] = None
    crop_fields: Optional[int] = None
    wood_bonus: Optional[int] = None
    clay_bonus: Optional[int] = None
    iron_bonus: Optional[int] = None
    crop_bonus: Optional[int] = None
    can_be_settled: Optional[bool] = None
    can_be_attacked: Optional[bool] = None


class TypeFieldResponse(TypeFieldBase):
    """Схема ответа типа поля."""
    id: int = Field(..., description="ID типа поля")
    model_config = ConfigDict(from_attributes=True)


# === MapCell Schemas ===

class MapCellBase(BaseModel):
    """Базовая схема ячейки карты."""
    server_id: int = Field(..., description="ID сервера")
    x: int = Field(..., description="X координата")
    y: int = Field(..., description="Y координата")
    type_id: int = Field(..., description="ID типа поля")


class MapCellCreate(MapCellBase):
    """Схема создания ячейки карты."""
    pass


class MapCellUpdate(BaseModel):
    """Схема обновления ячейки карты."""
    type_id: Optional[int] = None


class MapCellResponse(MapCellBase):
    """Схема ответа ячейки карты."""
    type_field: TypeFieldResponse = Field(..., description="Тип поля")
    model_config = ConfigDict(from_attributes=True)


# === MapFeature Schemas ===

class MapFeatureBase(BaseModel):
    """Базовая схема особенностей карты для заселяемых полей."""
    server_id: int = Field(..., description="ID сервера")
    x: int = Field(..., description="X координата")
    y: int = Field(..., description="Y координата")
    field_type: int = Field(..., description="Тип поля (6, 7, 9, 15)")
    oasis_wood: Optional[int] = Field(None, description="Аггрегированный бонус леса от оазисов")
    oasis_clay: Optional[int] = Field(None, description="Аггрегированный бонус глины от оазисов")
    oasis_iron: Optional[int] = Field(None, description="Аггрегированный бонус железа от оазисов")
    oasis_crop: Optional[int] = Field(None, description="Аггрегированный бонус зерна от оазисов")


class MapFeatureCreate(MapFeatureBase):
    """Схема создания особенностей карты."""
    pass


class MapFeatureUpdate(BaseModel):
    """Схема обновления особенностей карты."""
    field_type: Optional[int] = None
    oasis_wood: Optional[int] = None
    oasis_clay: Optional[int] = None
    oasis_iron: Optional[int] = None
    oasis_crop: Optional[int] = None


class MapFeatureResponse(MapFeatureBase):
    """Схема ответа особенностей карты."""
    model_config = ConfigDict(from_attributes=True)


# === Map Cell Search Schemas ===

class MapCellFilterRequest(BaseModel):
    """Схема запроса фильтров для поиска клеток карты."""
    type_ids: Optional[List[int]] = Field(None, description="Список ID типов клеток")
    min_crop: int = Field(0, ge=0, le=150, description="Минимальный бонус crop (%)")
    min_wood: int = Field(0, ge=0, le=150, description="Минимальный бонус wood (%)")
    min_clay: int = Field(0, ge=0, le=150, description="Минимальный бонус clay (%)")
    min_iron: int = Field(0, ge=0, le=150, description="Минимальный бонус iron (%)")
    occupied: Optional[bool] = Field(None, description="Занятость клетки: True-занята, False-свободна, None-любая")
    page: int = Field(1, ge=1, description="Номер страницы")
    per_page: int = Field(20, ge=1, le=100, description="Количество на страницу")


class MapCellSearchResponseItem(BaseModel):
    """Схема элемента ответа поиска клеток."""
    x: int = Field(..., description="X координата")
    y: int = Field(..., description="Y координата")
    type_id: int = Field(..., description="ID типа поля")
    type_name: str = Field(..., description="Название типа поля")
    oasis_crop: Optional[int] = Field(None, description="Бонус crop от оазисов (%)")
    oasis_wood: Optional[int] = Field(None, description="Бонус wood от оазисов (%)")
    oasis_clay: Optional[int] = Field(None, description="Бонус clay от оазисов (%)")
    oasis_iron: Optional[int] = Field(None, description="Бонус iron от оазисов (%)")
    occupied: bool = Field(..., description="Занята ли клетка")
    occupied_by: Optional[str] = Field(None, description="Кем занята (имя игрока/альянса)")


class MapCellSearchResponse(BaseModel):
    """Схема ответа поиска клеток карты."""
    cells: List[MapCellSearchResponseItem] = Field(..., description="Список найденных клеток")
    total: int = Field(..., description="Общее количество найденных клеток")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Количество на страницу")
    pages: int = Field(..., description="Общее количество страниц")


class MapAreaCell(BaseModel):
    """Схема клетки для отображения области карты."""
    x: int = Field(..., description="X координата")
    y: int = Field(..., description="Y координата")
    type_id: int = Field(..., description="ID типа поля")
    type_name: str = Field(..., description="Название типа поля")
    has_oasis: bool = Field(..., description="Есть ли оазис с бонусами")


class MapAreaResponse(BaseModel):
    """Схема ответа данных области карты."""
    center_x: int = Field(..., description="X координата центра")
    center_y: int = Field(..., description="Y координата центра")
    size: int = Field(..., description="Размер карты сервера (от -size до size)")
    cells: List[MapAreaCell] = Field(..., description="Список клеток 15x15 вокруг центра")

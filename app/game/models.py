from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Text, Boolean, DateTime, Time, ForeignKey, UniqueConstraint, Index, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.dao.database import Base

if TYPE_CHECKING:
    from app.auth.models import User


class UserSettings(Base):
    """Настройки пользователя."""
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)

    # Отношения
    user: Mapped["User"] = relationship("app.auth.models.User", back_populates="settings")


class Server(Base):
    """Игровые серверы."""
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, default={"server_time": "UTC+1", "speed": "x1", "server_type": "Classic", "Size": "400"}, nullable=False)
    update_time: Mapped[Optional[datetime]] = mapped_column(Time, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    is_updating: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_update_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_update_finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_update_info: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Отношения
    alliances: Mapped[List["Alliance"]] = relationship("Alliance", back_populates="server")
    players: Mapped[List["Player"]] = relationship("Player", back_populates="server")
    villages: Mapped[List["Village"]] = relationship("Village", back_populates="server")
    attacks: Mapped[List["Attack"]] = relationship("Attack", back_populates="server")
    user_servers: Mapped[List["UserServer"]] = relationship("UserServer", back_populates="server")
    map_updates: Mapped[List["MapUpdate"]] = relationship("MapUpdate", back_populates="server")
    maps: Mapped[List["MapCell"]] = relationship("MapCell", back_populates="server")
    map_features: Mapped[List["MapFeature"]] = relationship("MapFeature", back_populates="server")
    player_verifications: Mapped[List["PlayerVerification"]] = relationship("PlayerVerification", back_populates="server")


class UserServer(Base):
    """Связь пользователей с серверами."""
    __tablename__ = "user_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Отношения
    user: Mapped["User"] = relationship("app.auth.models.User", back_populates="user_servers")
    server: Mapped["Server"] = relationship("Server", back_populates="user_servers")

    __table_args__ = (
        UniqueConstraint("user_id", "server_id", name="uq_user_server"),
        Index("idx_user_servers_user_id", "user_id"),
    )


class Race(Base):
    """Расы."""
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Отношения
    players: Mapped[List["Player"]] = relationship("Player", back_populates="race")
    villages: Mapped[List["Village"]] = relationship("Village", back_populates="race")


class Alliance(Base):
    """Альянсы."""
    __tablename__ = "alliances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    alliance_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID из игры
    tag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    players_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    population: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Отношения
    server: Mapped["Server"] = relationship("Server", back_populates="alliances")
    players: Mapped[List["Player"]] = relationship("Player", back_populates="alliance")
    attacks: Mapped[List["Attack"]] = relationship("Attack", back_populates="alliance")

    __table_args__ = (
        UniqueConstraint("server_id", "alliance_id", name="uq_alliances_server_alliance_id"),
    )


class Player(Base):
    """Игроки."""
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)  # Связь с пользователем системы
    account_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False)  # ID из игры
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alliance_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("alliances.id"), nullable=True)
    population: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    villages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    race_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("races.id"), nullable=True)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Отношения
    server: Mapped["Server"] = relationship("Server", back_populates="players")
    alliance: Mapped[Optional["Alliance"]] = relationship("Alliance", back_populates="players")
    race: Mapped[Optional["Race"]] = relationship("Race", back_populates="players")
    villages: Mapped[List["Village"]] = relationship("Village", back_populates="player")
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="player")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="players")
    verification: Mapped[Optional["PlayerVerification"]] = relationship("PlayerVerification", back_populates="player", uselist=False)

    __table_args__ = (
        UniqueConstraint("server_id", "account_id", name="uq_players_server_account_id"),
    )


class Village(Base):
    """Деревни."""
    __tablename__ = "villages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    map_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    village_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    race_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("races.id"), nullable=True)
    village_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Отношения
    server: Mapped["Server"] = relationship("Server", back_populates="villages")
    player: Mapped[Optional["Player"]] = relationship("Player", back_populates="villages")
    race: Mapped[Optional["Race"]] = relationship("Race", back_populates="villages")
    attacks_as_target: Mapped[List["Attack"]] = relationship(
        "Attack",
        foreign_keys="Attack.target_village_id",
        back_populates="target_village"
    )

    __table_args__ = (
        UniqueConstraint("server_id", "village_id", name="uq_villages_server_village"),
    )


class ApiKey(Base):
    """API ключи для расширения браузера."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    key_value: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Отношения
    player: Mapped["Player"] = relationship("Player", back_populates="api_keys")
    server: Mapped["Server"] = relationship("Server")


class Attack(Base):
    """Атаки (нормализованная таблица)."""
    __tablename__ = "attacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    attacker_player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    target_village_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("villages.id"), nullable=True)
    defender_player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    alliance_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("alliances.id"), nullable=True)
    arrival_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attack_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # raid, attack, siege
    wave_group: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Отношения
    server: Mapped["Server"] = relationship("Server", back_populates="attacks")
    target_village: Mapped[Optional["Village"]] = relationship(
        "Village",
        foreign_keys=[target_village_id],
        back_populates="attacks_as_target"
    )
    alliance: Mapped[Optional["Alliance"]] = relationship("Alliance", back_populates="attacks")

    __table_args__ = (
        Index("idx_attacks_target_village_arrival", "target_village_id", "arrival_time"),
        Index("idx_attacks_alliance_arrival", "alliance_id", "arrival_time"),
        Index("idx_attacks_defender_arrival", "defender_player_id", "arrival_time"),
        Index("idx_attacks_server_arrival", "server_id", "arrival_time"),
    )


class MapUpdate(Base):
    """Логи обновлений карты серверов."""
    __tablename__ = "server_map_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)  # 'running', 'completed', 'failed'
    villages_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    players_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    alliances_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Отношения
    server: Mapped["Server"] = relationship("Server", back_populates="map_updates")


class TypeField(Base):
    """Типы полей карты."""
    __tablename__ = "type_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Oasis, Field 3-3-3-9, Forest, Lake, Mountain, Clay

    # Ресурсные поля (уровни)
    wood_fields: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1, 3, 4, 5
    clay_fields: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1, 3, 4, 5
    iron_fields: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1, 3, 4, 5
    crop_fields: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 6, 7, 9, 15

    # Бонусы
    wood_bonus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 25 or None
    clay_bonus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 25 or None
    iron_bonus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 25 or None
    crop_bonus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 25, 50 or None

    # Флаги
    can_be_settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_be_attacked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Отношения
    maps: Mapped[List["MapCell"]] = relationship("MapCell", back_populates="type_field")


class MapCell(Base):
    """Ячейки карты."""
    __tablename__ = "maps"

    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), primary_key=True)
    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("type_fields.id"), nullable=False)

    # Отношения
    server: Mapped["Server"] = relationship("Server", back_populates="maps")
    type_field: Mapped["TypeField"] = relationship("TypeField", back_populates="maps")

    __table_args__ = (
        Index("idx_maps_type", "type_id"),
    )


class MapFeature(Base):
    """Особенности карты для заселяемых полей."""
    __tablename__ = "map_features"

    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), primary_key=True)
    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 6, 7, 9, 15
    oasis_wood: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    oasis_clay: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    oasis_iron: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    oasis_crop: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Отношения
    server: Mapped["Server"] = relationship("Server", back_populates="map_features")

    __table_args__ = (
        Index("idx_map_features_field_type", "field_type"),
    )


class PlayerVerification(Base):
    """Подтверждение игрока пользователем."""
    __tablename__ = "player_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    verification_code: Mapped[str] = mapped_column(String(10), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Отношения
    user: Mapped["User"] = relationship("app.auth.models.User", back_populates="player_verifications")
    player: Mapped["Player"] = relationship("Player", back_populates="verification")
    server: Mapped["Server"] = relationship("Server", back_populates="player_verifications")

    __table_args__ = (
        UniqueConstraint("user_id", "player_id", name="uq_user_player"),
        Index("idx_player_verifications_user_id", "user_id"),
        Index("idx_player_verifications_player_id", "player_id"),
    )

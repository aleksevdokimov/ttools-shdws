from datetime import datetime
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.dao.database import Base, str_uniq

# Импорт моделей для корректной работы SQLAlchemy relationships
# Эти модели нужны для string references в relationship()
from app.game.models import UserSettings, UserServer, Player


class Role(Base):
    name: Mapped[str_uniq]
    users: Mapped[list["User"]] = relationship(back_populates="role")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"


class User(Base):
    username: Mapped[str_uniq]
    email: Mapped[str_uniq]
    deleted_at: Mapped[str] = mapped_column(default=None, nullable=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'), default=1, server_default=text("1"))
    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="joined")
    
    # Хеш пароля
    password_hash: Mapped[str] = mapped_column(default="", nullable=False)
    info: Mapped[str] = mapped_column(default=None, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Отношения к игровым моделям
    settings: Mapped["UserSettings"] = relationship("UserSettings", back_populates="user", uselist=False)
    user_servers: Mapped[list["UserServer"]] = relationship("UserServer", back_populates="user")
    players: Mapped[list["Player"]] = relationship("Player", back_populates="user")

    # Отношение к registration token
    registration_token: Mapped["RegistrationToken"] = relationship("RegistrationToken", back_populates="user", uselist=False)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"


class RegistrationToken(Base):
    token: Mapped[str] = mapped_column(unique=True, nullable=False)
    used_by_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    used_at: Mapped[datetime] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=True)
    comment: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Отношение к пользователю
    user: Mapped["User"] = relationship("User", back_populates="registration_token")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, token={self.token})"

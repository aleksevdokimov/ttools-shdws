import re
from datetime import datetime
from typing import Self
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator, computed_field


class EmailModel(BaseModel):
    email: EmailStr = Field(description="Электронная почта")
    model_config = ConfigDict(from_attributes=True)


class UsernameModel(BaseModel):
    username: str = Field(min_length=3, max_length=50, description="Логин пользователя, от 3 до 50 символов")
    model_config = ConfigDict(from_attributes=True)


class UserBase(EmailModel, UsernameModel):
    pass


class SUserRegister(UsernameModel, EmailModel):
    password: str = Field(min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    confirm_password: str = Field(min_length=5, max_length=50, description="Повторите пароль")
    token: str = Field(description="Регистрационный токен")

    @model_validator(mode="after")
    def check_password(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError("Пароли не совпадают")
        return self


class SUserAddDB(UsernameModel, EmailModel):
    password_hash: str = Field(default="", description="Хеш пароля")
    deleted_at: str | None = Field(default=None, description="Дата мягкого удаления")


class SUserAuth(UsernameModel):
    password: str = Field(min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")


class RoleModel(BaseModel):
    id: int = Field(description="Идентификатор роли")
    name: str = Field(description="Название роли")
    model_config = ConfigDict(from_attributes=True)


class SUserInfo(UserBase):
    id: int = Field(description="Идентификатор пользователя")
    role_id: int = Field(description="ID роли")
    role_name: str = Field(description="Название роли")
    is_active: bool = Field(description="Активность пользователя")
    info: str | None = Field(default=None, description="Дополнительная информация")
    deleted_at: str | None = Field(default=None, description="Дата удаления")
    # Дополнительные поля для UI
    selected_server_id: int | None = Field(default=None, description="ID выбранного сервера")
    selected_server_name: str | None = Field(default=None, description="Название выбранного сервера")
    player_name: str | None = Field(default=None, description="Имя игрока на сервере")
    model_config = ConfigDict(from_attributes=True)


class SUserUpdate(BaseModel):
    """Схема для обновления пользователя."""
    username: str | None = Field(default=None, min_length=3, max_length=50, description="Логин пользователя")
    email: EmailStr | None = Field(default=None, description="Электронная почта")
    is_active: bool | None = Field(default=None, description="Активность пользователя")
    role_id: int | None = Field(default=None, description="ID роли")
    info: str | None = Field(default=None, description="Дополнительная информация")
    model_config = ConfigDict(from_attributes=True)


class SUserCreate(UsernameModel, EmailModel):
    """Схема для создания пользователя админом."""
    password: str = Field(min_length=5, max_length=50, description="Пароль")
    is_active: bool = Field(default=True, description="Активность пользователя")
    role_id: int = Field(default=1, description="ID роли")
    info: str | None = Field(default=None, description="Дополнительная информация")


class SPasswordReset(BaseModel):
    """Схема для сброса пароля."""
    new_password: str = Field(min_length=5, max_length=50, description="Новый пароль")


class SUserListResponse(BaseModel):
    """Схема ответа со списком пользователей и пагинацией."""
    users: list[SUserInfo] = Field(description="Список пользователей")
    total: int = Field(description="Общее количество пользователей")
    page: int = Field(description="Текущая страница")
    per_page: int = Field(description="Записей на странице")
    pages: int = Field(description="Всего страниц")


class SRoleInfo(BaseModel):
    """Схема для информации о роли."""
    id: int = Field(description="ID роли")
    name: str = Field(description="Название роли")
    model_config = ConfigDict(from_attributes=True)


class SRegistrationTokenCreate(BaseModel):
    """Схема для создания регистрационного токена."""
    token: str = Field(description="Уникальный токен")
    comment: str | None = Field(default=None, description="Комментарий к токену")
    expires_at: datetime | None = Field(default=None, description="Дата истечения токена")


class SRegistrationToken(BaseModel):
    """Схема для чтения регистрационного токена."""
    id: int = Field(description="ID токена")
    token: str = Field(description="Уникальный токен")
    used_by_user_id: int | None = Field(default=None, description="ID пользователя, использовавшего токен")
    used_at: datetime | None = Field(default=None, description="Дата использования токена")
    expires_at: datetime | None = Field(default=None, description="Дата истечения токена")
    comment: str | None = Field(default=None, description="Комментарий к токену")
    created_at: datetime = Field(description="Дата создания токена")
    model_config = ConfigDict(from_attributes=True)


class SRegistrationTokenUpdate(BaseModel):
    """Схема для обновления регистрационного токена."""
    comment: str | None = Field(default=None, description="Комментарий к токену")
    expires_at: datetime | None = Field(default=None, description="Дата истечения токена")


class SRegistrationTokenListResponse(BaseModel):
    """Схема ответа со списком токенов."""
    tokens: list[SRegistrationToken] = Field(description="Список токенов")
    total: int = Field(description="Общее количество токенов")
    page: int = Field(description="Текущая страница")
    per_page: int = Field(description="Записей на странице")
    pages: int = Field(description="Всего страниц")


class SGenerateKeysRequest(BaseModel):
    """Схема запроса для генерации ключей."""
    count: int = Field(ge=1, le=30, description="Количество ключей для генерации")

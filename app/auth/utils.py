from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi.responses import Response
from app.config import settings


def create_tokens(data: dict) -> dict:
    # Текущее время в UTC
    now = datetime.now(timezone.utc)

    # AccessToken - 30 минут
    access_expire = now + timedelta(minutes=30)
    access_payload = data.copy()
    access_payload.update({"exp": int(access_expire.timestamp()), "type": "access"})
    access_token = jwt.encode(
        access_payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    # RefreshToken - 7 дней
    refresh_expire = now + timedelta(days=7)
    refresh_payload = data.copy()
    refresh_payload.update({"exp": int(refresh_expire.timestamp()), "type": "refresh"})
    refresh_token = jwt.encode(
        refresh_payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


async def authenticate_user(user, password):
    if not user:
        return None
    is_valid = verify_password(plain_password=password, hashed_password=user.password_hash)
    return user if is_valid else None


def set_tokens(response: Response, user_id: int):
    new_tokens = create_tokens(data={"sub": str(user_id)})
    access_token = new_tokens.get('access_token')
    refresh_token = new_tokens.get("refresh_token")

    # Для localhost (DEBUG=True) отключаем secure=True, иначе куки не установятся на HTTP
    secure = not settings.DEBUG

    response.set_cookie(
        key="user_access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=60 * 30  # 30 минут - соответствует времени жизни access токена
    )

    response.set_cookie(
        key="user_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 7  # 7 дней - соответствует времени жизни refresh токена
    )


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

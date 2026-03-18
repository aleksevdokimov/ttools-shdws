from fastapi import status, HTTPException

# Пользователь уже существует
UserAlreadyExistsException = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail='Пользователь уже существует'
)

# Сервер уже существует
ServerAlreadyExistsException = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail='Сервер с таким URL уже существует'
)

# URL сервера уже существует
ServerUrlAlreadyExistsException = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail='URL сервера уже существует'
)

# Пользователь не найден
UserNotFoundException = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail='Пользователь не найден'
)

# Отсутствует идентификатор пользователя
UserIdNotFoundException = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail='Отсутствует идентификатор пользователя'
)

# Неверный логин или пароль
IncorrectEmailOrPasswordException = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail='Неверный логин или пароль'
)

# Токен истек
TokenExpiredException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Токен истек'
)

# Некорректный формат токена
InvalidTokenFormatException = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail='Некорректный формат токена'
)


# Токен отсутствует в заголовке
TokenNoFound = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Токен отсутствует в заголовке'
)

# Невалидный JWT токен
NoJwtException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Токен не валидный'
)

# Не найден ID пользователя
NoUserIdException = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail='Не найден ID пользователя'
)

# Недостаточно прав
class ForbiddenException(HTTPException):
    def __init__(self, detail: str = 'Недостаточно прав'):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

TokenInvalidFormatException = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат токена. Ожидается 'Bearer <токен>'"
)

# Сервер не найден
class ServerNotFoundException(HTTPException):
    def __init__(self, detail: str = 'Сервер не найден'):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

# Сервер не добавлен пользователю
class UserServerNotFoundException(HTTPException):
    def __init__(self, detail: str = 'Сервер не добавлен в ваш список'):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
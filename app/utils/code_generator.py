import base64
import random
import string
import urllib.parse


def decode_player_name(encoded_name: str) -> str:
    """
    Декодирует имя игрока из base64.
    
    Args:
        encoded_name: Закодированное имя в base64
        
    Returns:
        Декодированное имя игрока
    """
    if not encoded_name:
        return ""
    try:
        decoded_bytes = base64.b64decode(encoded_name)
        decoded_str = decoded_bytes.decode('utf-8')
        return urllib.parse.unquote(decoded_str)
    except Exception:
        return encoded_name


def generate_verification_code(length: int = 8) -> str:
    """
    Генерация кода подтверждения.
    
    Args:
        length: Длина кода (по умолчанию 8)
        
    Returns:
        Строка из заглавных букв и цифр
    """
    characters = string.ascii_uppercase + string.digits
    # Исключаем похожие символы для удобства ввода
    characters = characters.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    
    return ''.join(random.choices(characters, k=length))
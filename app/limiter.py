from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter - использует IP-адрес клиента
limiter = Limiter(key_func=get_remote_address)

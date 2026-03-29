# app/presentation/dependencies/game_dep.py
"""Dependencies для игровых данных (presentation layer)"""

from typing import Optional
from fastapi import Depends
from app.game.dao import ServerDAO
from app.dependencies.dao_dep import get_session_without_commit
from sqlalchemy.ext.asyncio import AsyncSession


async def get_server(
    server_id: int,
    session: AsyncSession = Depends(get_session_without_commit),
) -> Optional[dict]:
    """
    Получить сервер по ID.
    Возвращает None если не найден.
    """
    server_dao = ServerDAO(session)
    return await server_dao.find_one_or_none_by_id(server_id)
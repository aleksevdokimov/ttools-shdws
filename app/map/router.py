"""
Роутер для API загрузки карты.
"""
from fastapi import APIRouter

from app.game.schemas import TilesBatch, TilesUploadResponse
from app.services.map_upload import map_upload_service

router = APIRouter(tags=["Map"])


@router.post("/api/map/load", response_model=TilesUploadResponse)
async def upload_tiles(batch: TilesBatch) -> TilesUploadResponse:
    """
    Загрузка данных карты (тайлов) с внешнего источника.
    
    Публичный API без аутентификации.
    Сохраняет полученные данные в JSON формате в директорию map_history.
    """
    # Сохраняем данные через сервис
    result = await map_upload_service.save_tiles(batch)
    
    return TilesUploadResponse(
        status="ok",
        tiles_count=result["tiles_count"],
        filename=result["filename"]
    )

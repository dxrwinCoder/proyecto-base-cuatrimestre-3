from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from models.miembro import Miembro
from utils.auth import obtener_miembro_actual
from services.notificacion_service import listar_notificaciones_por_miembro
from schemas.notificacion import Notificacion

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


@router.get("/mias", response_model=list[Notificacion])
async def mis_notificaciones(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    return await listar_notificaciones_por_miembro(db, current_user.id)

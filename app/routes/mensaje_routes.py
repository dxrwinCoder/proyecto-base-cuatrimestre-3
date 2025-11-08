from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from models.miembro import Miembro
from services.mensaje_service import obtener_mensajes_por_hogar
from utils.auth import obtener_miembro_actual
from schemas.mensaje import MensajeResponse

router = APIRouter(prefix="/mensajes", tags=["Mensajes"])


@router.get("/hogar/{hogar_id}", response_model=list[MensajeResponse])
async def listar_mensajes(
    hogar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    if current_user.id_hogar != hogar_id:
        raise HTTPException(status_code=403, detail="No perteneces a este hogar")

    mensajes = await obtener_mensajes_por_hogar(db, hogar_id)
    return mensajes

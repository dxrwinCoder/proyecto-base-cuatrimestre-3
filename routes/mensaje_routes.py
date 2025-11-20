from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from models.miembro import Miembro
from services.mensaje_service import (
    obtener_mensajes_por_hogar,
    enviar_mensaje_directo,
    listar_conversacion_directa,
)
from utils.auth import obtener_miembro_actual
from schemas.mensaje import MensajeResponse, MensajeCreate
from utils.permissions import require_permission

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


@router.post(
    "/directo/{destinatario_id}",
    response_model=MensajeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("Mensajes", "crear"))],
)
async def enviar_directo(
    destinatario_id: int,
    payload: MensajeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    # Forzar hogar y remitente desde el token/usuario
    if payload.id_hogar != current_user.id_hogar:
        raise HTTPException(status_code=403, detail="No puedes enviar a otro hogar")

    try:
        mensaje = await enviar_mensaje_directo(
            db,
            id_hogar=current_user.id_hogar,
            remitente_id=current_user.id,
            destinatario_id=destinatario_id,
            contenido=payload.contenido,
        )
        await db.commit()
        await db.refresh(mensaje)
        return mensaje
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/directo/{otro_id}",
    response_model=list[MensajeResponse],
    dependencies=[Depends(require_permission("Mensajes", "leer"))],
)
async def conversacion_directa(
    otro_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    mensajes = await listar_conversacion_directa(
        db, current_user.id_hogar, current_user.id, otro_id
    )
    return mensajes

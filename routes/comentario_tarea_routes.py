# routes/comentario_tarea_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.miembro import Miembro
from utils.auth import obtener_miembro_actual
from utils.permissions import require_permission
from utils.logger import setup_logger

from schemas.comentario_tarea import ComentarioTareaCreate, ComentarioTarea
from services.tarea_service import (
    agregar_comentario_a_tarea,
    obtener_tarea_por_id,
    listar_comentarios_por_tarea as service_listar_comentarios,
)

logger = setup_logger("comentario_tarea_routes")

router = APIRouter(prefix="/comentarios-tarea", tags=["Comentarios y Evidencia"])


@router.post(
    "/",
    response_model=ComentarioTarea,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("Tareas", "leer"))],
)
async def crear_comentario_endpoint(
    comentario_data: ComentarioTareaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    """
    Crea un comentario en una tarea del mismo hogar.
    - Seguridad: valida existencia de la tarea y pertenencia al hogar.
    - Transacción: el servicio hace flush y la ruta confirma con commit.
    """
    try:
        tarea = await obtener_tarea_por_id(db, comentario_data.id_tarea)
        if not tarea:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La tarea no existe.",
            )

        if tarea.id_hogar != current_user.id_hogar:
            logger.warning(
                f"Intento no autorizado de comentar en tarea de otro hogar por usuario {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para comentar en esta tarea.",
            )

        comentario_creado = await agregar_comentario_a_tarea(
            db, data=comentario_data, miembro_id=current_user.id
        )

        await db.commit()
        return comentario_creado

    except (ValueError, Exception) as e:
        await db.rollback()
        logger.error(f"Error al crear comentario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al crear el comentario: {str(e)}",
        )


@router.get(
    "/tarea/{tarea_id}",
    response_model=list[ComentarioTarea],
    dependencies=[Depends(require_permission("Tareas", "leer"))],
)
async def listar_comentarios_por_tarea(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    """
    Lista comentarios activos de una tarea, validando que pertenezca al mismo hogar.
    """
    tarea = await obtener_tarea_por_id(db, tarea_id)
    if not tarea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
        )
    if tarea.id_hogar != current_user.id_hogar:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver comentarios de otro hogar",
        )

    try:
        return await service_listar_comentarios(db, tarea_id)
    except Exception as e:
        logger.error(f"Error al listar comentarios de la tarea {tarea_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar comentarios",
        )

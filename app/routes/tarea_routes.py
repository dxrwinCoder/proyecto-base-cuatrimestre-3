from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.tarea import TareaCreate, TareaUpdate, Tarea
from services.tarea_service import (
    crear_tarea,
    obtener_tarea_por_id,
    listar_tareas_por_miembro,
    listar_tareas_por_evento,
    listar_tareas_por_tipo,
    actualizar_estado_tarea,
)
from utils.auth import obtener_miembro_actual
from utils.permissions import require_permission
from utils.logger import setup_logger

logger = setup_logger("tarea_routes")

router = APIRouter(prefix="/tareas", tags=["Tareas"])


@router.post(
    "/",
    response_model=Tarea,
    dependencies=[Depends(require_permission("Tareas", "crear"))],
)
async def crear_tarea_endpoint(
    tarea: TareaCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(obtener_miembro_actual),
):
    try:
        if tarea.id_hogar != current_user.id_hogar:
            logger.warning(
                f"Usuario {current_user.id} intentó crear tarea en hogar ajeno"
            )
            raise HTTPException(
                status_code=403, detail="No puedes crear tareas en otro hogar"
            )
        return await crear_tarea(db, tarea.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear tarea: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/{tarea_id}",
    response_model=Tarea,
    dependencies=[Depends(require_permission("Tareas", "leer"))],
)
async def ver_tarea(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(obtener_miembro_actual),
):
    try:
        tarea = await obtener_tarea_por_id(db, tarea_id)
        if not tarea or tarea.id_hogar != current_user.id_hogar:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        return tarea
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener tarea {tarea_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno")


@router.get("/mias", response_model=list[Tarea])
async def listar_mis_tareas(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(obtener_miembro_actual),
):
    try:
        return await listar_tareas_por_miembro(db, current_user.id)
    except Exception as e:
        logger.error(f"Error al listar tareas del usuario {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno")


@router.put("/{tarea_id}/estado", response_model=Tarea)
async def cambiar_estado_tarea(
    tarea_id: int,
    update: TareaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(obtener_miembro_actual),
):
    try:
        if update.estado_actual not in ["en_progreso", "completada", "cancelada"]:
            raise HTTPException(status_code=400, detail="Estado no válido")
        tarea = await actualizar_estado_tarea(
            db, tarea_id, update.estado_actual, current_user.id
        )
        if not tarea:
            raise HTTPException(
                status_code=403, detail="No autorizado o tarea inexistente"
            )
        return tarea
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar estado de tarea {tarea_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno")

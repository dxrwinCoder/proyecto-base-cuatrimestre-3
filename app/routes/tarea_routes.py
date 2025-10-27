from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.tarea import TareaCreate, Tarea, TareaUpdate
from services.tarea_service import crear_tarea
from utils.permissions import require_permission
from utils.logger import setup_logger

logger = setup_logger("tarea_routes")

router = APIRouter(prefix="/tareas", tags=["Tareas"])


@router.post("/", response_model=Tarea)
async def crear_tarea_endpoint(
    tarea: TareaCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("Tareas", "crear")),
):
    try:
        logger.info(f"Intentando crear tarea: {tarea.titulo}")
        tarea_dict = tarea.model_dump()
        tarea_dict["id_hogar"] = (
            user.id_hogar
        )  # Asegurar que la tarea pertenezca al hogar del usuario
        resultado = await crear_tarea(db, tarea_dict)
        logger.info(f"Tarea creada exitosamente: {resultado.id}")
        return resultado
    except Exception as e:
        logger.error(f"Error al crear tarea: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al crear la tarea")


@router.get("/", response_model=list[Tarea])
async def listar_tareas(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("Tareas", "leer")),
):
    try:
        logger.info(f"Listando tareas para el hogar: {user.id_hogar}")
        tareas = await listar_tareas_por_hogar(db, user.id_hogar)
        logger.info(f"Se encontraron {len(tareas)} tareas")
        return tareas
    except Exception as e:
        logger.error(f"Error al listar tareas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al listar las tareas")


@router.get("/{tarea_id}", response_model=Tarea)
async def obtener_tarea_endpoint(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("Tareas", "leer")),
):
    try:
        logger.info(f"Buscando tarea: {tarea_id}")
        tarea = await obtener_tarea(db, tarea_id)
        if not tarea:
            logger.warning(f"Tarea no encontrada: {tarea_id}")
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        if tarea.id_hogar != user.id_hogar:
            logger.warning(f"Intento de acceso no autorizado a tarea: {tarea_id}")
            raise HTTPException(status_code=403, detail="No autorizado")
        return tarea
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener tarea: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener la tarea")


@router.patch("/{tarea_id}", response_model=Tarea)
async def actualizar_tarea_endpoint(
    tarea_id: int,
    tarea: TareaUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("Tareas", "actualizar")),
):
    try:
        logger.info(f"Actualizando tarea: {tarea_id}")
        tarea_actual = await obtener_tarea(db, tarea_id)
        if not tarea_actual:
            logger.warning(f"Tarea no encontrada para actualizar: {tarea_id}")
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        if tarea_actual.id_hogar != user.id_hogar:
            logger.warning(
                f"Intento de actualización no autorizada de tarea: {tarea_id}"
            )
            raise HTTPException(status_code=403, detail="No autorizado")

        tarea_actualizada = await actualizar_tarea(
            db, tarea_id, tarea.model_dump(exclude_unset=True)
        )
        logger.info(f"Tarea actualizada exitosamente: {tarea_id}")
        return tarea_actualizada
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar tarea: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar la tarea")


@router.delete("/{tarea_id}")
async def eliminar_tarea_endpoint(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("Tareas", "eliminar")),
):
    try:
        logger.info(f"Eliminando tarea: {tarea_id}")
        tarea = await obtener_tarea(db, tarea_id)
        if not tarea:
            logger.warning(f"Tarea no encontrada para eliminar: {tarea_id}")
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        if tarea.id_hogar != user.id_hogar:
            logger.warning(f"Intento de eliminación no autorizada de tarea: {tarea_id}")
            raise HTTPException(status_code=403, detail="No autorizado")

        resultado = await eliminar_tarea_logico(db, tarea_id)
        if resultado:
            logger.info(f"Tarea eliminada exitosamente: {tarea_id}")
            return {"message": "Tarea eliminada exitosamente"}
        raise HTTPException(status_code=400, detail="No se pudo eliminar la tarea")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar tarea: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar la tarea")


@router.patch("/{tarea_id}/completar", response_model=Tarea)
async def marcar_tarea_completada(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("Tareas", "actualizar")),
):
    try:
        logger.info(f"Marcando tarea como completada: {tarea_id}")
        tarea = await obtener_tarea(db, tarea_id)
        if not tarea:
            logger.warning(
                f"Tarea no encontrada para marcar como completada: {tarea_id}"
            )
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        if tarea.id_hogar != user.id_hogar:
            logger.warning(
                f"Intento no autorizado de marcar tarea como completada: {tarea_id}"
            )
            raise HTTPException(status_code=403, detail="No autorizado")

        tarea_actualizada = await marcar_completada(db, tarea_id)
        if tarea_actualizada:
            logger.info(f"Tarea marcada como completada exitosamente: {tarea_id}")
            return tarea_actualizada
        raise HTTPException(
            status_code=400, detail="No se pudo marcar la tarea como completada"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al marcar tarea como completada: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error al marcar la tarea como completada"
        )

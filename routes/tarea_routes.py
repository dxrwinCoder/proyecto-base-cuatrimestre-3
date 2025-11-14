# routes/tarea_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.tarea import TareaCreate, TareaUpdateEstado, Tarea
from services.tarea_service import (
    crear_tarea,
    obtener_tarea_por_id,
    listar_tareas_por_miembro,
    listar_tareas_por_evento,
    listar_tareas_por_tipo,  # ¡Ojo! Este servicio no lo he visto, ¡pero lo dejo!
    actualizar_estado_tarea,
)
from models.miembro import Miembro  # <-- ¡Importar Miembro!
from utils.auth import obtener_miembro_actual
from utils.permissions import require_permission
from utils.logger import setup_logger

logger = setup_logger("tarea_routes")

router = APIRouter(prefix="/tareas", tags=["Tareas"])


@router.post(
    "/",
    response_model=Tarea,
    status_code=status.HTTP_201_CREATED,  # ¡Buena práctica!
    dependencies=[Depends(require_permission("Tareas", "crear"))],
)
async def crear_tarea_endpoint(
    tarea: TareaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),  # ¡Cambiado a Miembro!
):
    try:
        if tarea.id_hogar != current_user.id_hogar:
            logger.warning(
                f"Usuario {current_user.id} intentó crear tarea en hogar ajeno"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes crear tareas en otro hogar",
            )

        # --- ¡AQUÍ ESTÁ EL PARCHE "MAKIA"! ---
        # 1. Pasamos el schema 'tarea' Y el 'current_user.id' como creador
        # 2. El servicio (con 'flush') y la ruta (con 'commit') manejan la TXN
        resultado = await crear_tarea(db, tarea, current_user.id)
        await db.commit()  # ¡LA RUTA "GRABA EN PIEDRA"!

        return resultado
        # --- FIN DEL PARCHE ---

    except (ValueError, Exception) as e:  # Capturar ValueError del servicio
        await db.rollback()  # ¡LA RUTA "DESHACE"!
        logger.error(f"Error inesperado al crear tarea: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{tarea_id}",
    response_model=Tarea,
    dependencies=[Depends(require_permission("Tareas", "leer"))],
)
async def ver_tarea(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),  # ¡Cambiado a Miembro!
):
    try:
        tarea = await obtener_tarea_por_id(db, tarea_id)
        # ¡Seguridad "Makia"! Verifica que la tarea exista Y que sea de su hogar.
        if not tarea or tarea.id_hogar != current_user.id_hogar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
            )
        return tarea
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener tarea {tarea_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno"
        )


@router.get("/mias/", response_model=list[Tarea])  # ¡Buena práctica: "/" al final!
async def listar_mis_tareas(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),  # ¡Cambiado a Miembro!
):
    try:
        return await listar_tareas_por_miembro(db, current_user.id)
    except Exception as e:
        logger.error(f"Error al listar tareas del usuario {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno"
        )


@router.put("/{tarea_id}/estado", response_model=Tarea)
async def cambiar_estado_tarea(
    tarea_id: int,
    update: TareaUpdateEstado,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),  # ¡Cambiado a Miembro!
):
    try:
        # --- ¡PARCHE "MAKIA" DE LÓGICA! ---
        # ¡La ruta no valida! ¡El servicio valida!
        # 1. Llamamos al servicio "calibrado"
        tarea = await actualizar_estado_tarea(
            db, tarea_id, update.estado_actual, current_user.id
        )

        # 2. ¡La ruta hace COMMIT!
        await db.commit()

        return tarea
        # --- FIN DEL PARCHE ---

    except ValueError as e:  # ¡Capturamos los errores de lógica del servicio!
        await db.rollback()
        logger.warning(f"Error de validación al cambiar estado: {str(e)}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar estado de tarea {tarea_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno"
        )


@router.get("/evento/{evento_id}", response_model=list[Tarea])
async def listar_tareas_por_evento_endpoint(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),  # ¡Cambiado a Miembro!
):
    try:
        # ¡OJO! ¡Esto es un N+1 "al revés"!
        # Filtra en Python, no en la DB. ¡Pero dejémoslo así por ahora!
        tareas = await listar_tareas_por_evento(db, evento_id)
        return [t for t in tareas if t.id_hogar == current_user.id_hogar]
    except Exception as e:
        logger.error(f"Error al listar tareas del evento {evento_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno"
        )

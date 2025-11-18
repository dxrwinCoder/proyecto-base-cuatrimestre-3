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
    listar_todas_tareas_hogar,
    listar_tareas_creadas_por_mi,
    listar_tareas_proximas_a_vencer,
    listar_tareas_en_proceso,
    actualizar_estado_tarea,
)

from datetime import date
from models.miembro import Miembro
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
    current_user: Miembro = Depends(obtener_miembro_actual),
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

        resultado = await crear_tarea(db, tarea, current_user.id)
        await db.commit()

        return resultado

    except (ValueError, Exception) as e:
        await db.rollback()
        logger.error(f"Error inesperado al crear tarea: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/mias/", response_model=list[Tarea])
async def listar_mis_tareas(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    try:
        return await listar_tareas_por_miembro(db, current_user.id)
    except Exception as e:
        logger.error(f"Error al listar tareas del usuario {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno"
        )


@router.get("/hogar/todas", response_model=list[Tarea])
async def listar_todas_las_tareas_hogar(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(
        require_permission("Tareas", "leer")
    ),  # Permiso especial sugerido
):
    """
    (Req 1 y 6) Admin consulta TODAS las tareas del hogar.
    Incluye comentarios recientes (vía eager loading en el servicio).
    Nota sobre Multi-Hogar: Si el usuario perteneciera a múltiples hogares,
    aquí se iteraría sobre una lista de current_user.hogares_ids.
    Por ahora, usamos current_user.id_hogar.
    """
    return await listar_todas_tareas_hogar(db, current_user.id_hogar)


@router.get("/asignadas-por-mi", response_model=list[Tarea])
async def listar_mis_asignaciones(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Tareas", "leer")),
):
    """(Req 2) Lista tareas activas que este usuario (Admin) asignó a otros."""
    return await listar_tareas_creadas_por_mi(db, current_user.id)


@router.get("/proximas-vencer", response_model=list[Tarea])
async def listar_vencimiento_proximo(
    fecha_tope: date,  # Parametro de query: ?fecha_tope=2025-12-31
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Tareas", "leer")),
):
    """Filtro manual de fecha para tareas próximas a vencer."""
    return await listar_tareas_proximas_a_vencer(db, current_user.id_hogar, fecha_tope)


@router.get("/en-proceso", response_model=list[Tarea])
async def listar_tareas_en_proceso_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Tareas", "leer")),
):
    """Lista solo las tareas en estado 'en_progreso'."""
    return await listar_tareas_en_proceso(db, current_user.id_hogar)


@router.get("/evento/{evento_id}", response_model=list[Tarea])
async def listar_tareas_por_evento_endpoint(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),  # ¡Cambiado a Miembro!
):
    try:

        tareas = await listar_tareas_por_evento(db, evento_id)
        return [t for t in tareas if t.id_hogar == current_user.id_hogar]
    except Exception as e:
        logger.error(f"Error al listar tareas del evento {evento_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno"
        )


@router.get(
    "/{tarea_id}",
    response_model=Tarea,
    dependencies=[Depends(require_permission("Tareas", "leer"))],
)
async def ver_tarea(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    try:
        tarea = await obtener_tarea_por_id(db, tarea_id)

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


@router.put("/{tarea_id}/estado", response_model=Tarea)
async def cambiar_estado_tarea(
    tarea_id: int,
    update: TareaUpdateEstado,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),  # ¡Cambiado a Miembro!
):
    try:

        tarea = await actualizar_estado_tarea(
            db, tarea_id, update.estado_actual, current_user.id
        )

        # 2. ¡La ruta hace COMMIT!
        await db.commit()

        return tarea

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


@router.get("/miembro/{miembro_id}", response_model=list[Tarea])
async def listar_tareas_de_miembro(
    miembro_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(
        require_permission("Tareas", "leer")
    ),  # Admin leyendo a otros
):
    """Admin lista las tareas de un miembro específico."""
    # Validación de seguridad: ¿El miembro pertenece a mi hogar?
    # (Se podría agregar una validación rápida aquí usando miembro_service)
    return await listar_tareas_por_miembro(db, miembro_id)


@router.get("/evento-proximo/{evento_id}", response_model=list[Tarea])
async def listar_tareas_evento_proximo(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Tareas", "leer")),
):
    """Lista tareas de un evento."""

    return await listar_tareas_por_evento(db, evento_id)

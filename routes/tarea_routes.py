# routes/tarea_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.tarea import TareaCreate, TareaUpdateEstado, Tarea, TareaUpdate
from schemas.comentario_tarea import ComentarioTarea
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
    agregar_comentario_con_imagen,
    actualizar_tarea,
    eliminar_tarea,
)

from datetime import date
from models.miembro import Miembro
from services.miembro_service import obtener_miembro
from fastapi import UploadFile, File, Form, Request
from utils.auth import obtener_miembro_actual
from utils.permissions import require_permission
from utils.logger import setup_logger
from datetime import datetime
from models.tarea import Tarea as TareaModel

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


@router.put(
    "/{tarea_id}",
    response_model=Tarea,
    dependencies=[Depends(require_permission("Tareas", "actualizar"))],
)
async def actualizar_tarea_endpoint(
    tarea_id: int,
    updates: TareaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    tarea_db = await db.get(TareaModel, tarea_id)
    if not tarea_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
        )

    if current_user.id_rol != 1 and tarea_db.id_hogar != current_user.id_hogar:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar tareas de otro hogar",
        )

    try:
        resultado = await actualizar_tarea(db, tarea_id, updates)
        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
            )
        await db.commit()
        return resultado
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar tarea {tarea_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno",
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


@router.get("/mias/detalle-tiempo", response_model=list[Tarea])
async def mis_tareas_con_tiempo(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    tareas = await listar_tareas_por_miembro(db, current_user.id)
    # Añadir campos con tiempos (se agregan dinámicamente; el schema ignorará extras)
    now = datetime.now()
    for t in tareas:
        if t.fecha_asignacion:
            t.tiempo_transcurrido_min = int((now - t.fecha_asignacion).total_seconds() // 60)
        if t.fecha_limite:
            t.tiempo_restante_min = int((t.fecha_limite - now.date()).total_seconds() // 60)
    return tareas


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


@router.delete(
    "/{tarea_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("Tareas", "eliminar"))],
)
async def eliminar_tarea_endpoint(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    tarea_db = await db.get(TareaModel, tarea_id)
    if not tarea_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
        )

    if current_user.id_rol != 1 and tarea_db.id_hogar != current_user.id_hogar:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar tareas de otro hogar",
        )

    try:
        resultado = await eliminar_tarea(db, tarea_id)
        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
            )
        await db.commit()
        return {"mensaje": "Tarea eliminada", "id": tarea_id}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al eliminar tarea {tarea_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno",
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
    # Validación de seguridad: el miembro debe pertenecer al mismo hogar, salvo que el usuario sea admin.
    miembro_obj = await obtener_miembro(db, miembro_id)
    if not miembro_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado"
        )

    if current_user.id_rol != 1 and miembro_obj.id_hogar != current_user.id_hogar:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver tareas de un miembro de otro hogar",
        )

    return await listar_tareas_por_miembro(db, miembro_id)


@router.get("/evento-proximo/{evento_id}", response_model=list[Tarea])
async def listar_tareas_evento_proximo(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Tareas", "leer")),
):
    """Lista tareas de un evento."""

    return await listar_tareas_por_evento(db, evento_id)


@router.post(
    "/{tarea_id}/comentarios/imagen",
    response_model=ComentarioTarea,
    dependencies=[Depends(require_permission("Tareas", "leer"))],
)
async def comentar_con_imagen(
    tarea_id: int,
    request: Request,
    contenido: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    """
    Adjunta imagen local a una tarea como comentario. Guarda archivo y persiste url_imagen.
    """
    tarea = await obtener_tarea_por_id(db, tarea_id)
    if not tarea or tarea.id_hogar != current_user.id_hogar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
        )

    try:
        form = await request.form()
        archivo = None
        for v in form.values():
            if isinstance(v, UploadFile):
                archivo = v
                break
        if archivo is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se adjuntó archivo de imagen",
            )
        # Si el campo 'contenido' no llegó en el form, usa el param por defecto
        contenido_form = form.get("contenido")
        if contenido_form is not None:
            contenido = contenido_form

        comentario = await agregar_comentario_con_imagen(
            db=db,
            tarea_id=tarea_id,
            miembro_id=current_user.id,
            contenido=contenido,
            archivo=archivo,
            media_root="utils/src",
        )
        await db.commit()
        return comentario
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al adjuntar imagen a tarea {tarea_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al adjuntar imagen",
        )

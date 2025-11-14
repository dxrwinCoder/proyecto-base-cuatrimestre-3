# services/tarea_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.tarea import Tarea
from models.comentario_tarea import ComentarioTarea
from models.miembro import Miembro
import time
from utils.logger import setup_logger


from services.notificacion_service import crear_notificacion
from schemas.notificacion import NotificacionCreate
from schemas.tarea import TareaCreate  # ¡Asumiendo que tiene TareaCreate!
from schemas.comentario_tarea import (
    ComentarioTareaCreate,
)

logger = setup_logger("tarea_service")


async def crear_tarea(db: AsyncSession, data: TareaCreate, creador_id: int):
    try:
        logger.info(f"Creando tarea con datos: {data.titulo}")

        tarea_data = data.model_dump()
        tarea_data["creado_por"] = creador_id

        tarea = Tarea(**tarea_data)
        db.add(tarea)

        await db.flush()
        await db.refresh(tarea)

        logger.info(f"Tarea creada (sin commit) con ID: {tarea.id}")

        if tarea.asignado_a != creador_id:
            notif_data = NotificacionCreate(
                id_miembro_destino=tarea.asignado_a,
                id_miembro_origen=creador_id,
                id_tarea=tarea.id,
                tipo="nueva_tarea",
                mensaje=f"Se te asignó una nueva tarea: '{tarea.titulo}'",
            )
            await crear_notificacion(db, notif_data)

        return tarea
    except Exception as e:
        logger.error(f"Error al crear tarea: {str(e)}")
        raise


async def obtener_tarea_por_id(db: AsyncSession, tarea_id: int):
    try:
        logger.info(f"Buscando tarea con ID: {tarea_id}")
        tarea = await db.get(Tarea, tarea_id)
        if not tarea or not tarea.estado:
            logger.warning(f"Tarea con ID {tarea_id} no encontrada o inactiva")
            return None
        logger.info(f"Tarea encontrada: {tarea.titulo}")
        return tarea
    except Exception as e:
        logger.error(f"Error al obtener tarea {tarea_id}: {str(e)}")
        raise


async def listar_tareas_por_miembro(db: AsyncSession, miembro_id: int):
    try:
        logger.info(f"Listando tareas asignadas al miembro ID: {miembro_id}")
        stmt = select(Tarea).where(Tarea.asignado_a == miembro_id, Tarea.estado == True)
        result = await db.execute(stmt)
        tareas = result.scalars().all()
        logger.info(
            f"Se encontraron {len(tareas)} tareas activas para el miembro {miembro_id}"
        )
        return tareas
    except Exception as e:
        logger.error(f"Error al listar tareas del miembro {miembro_id}: {str(e)}")
        raise


async def listar_tareas_por_evento(db: AsyncSession, evento_id: int):
    try:
        logger.info(f"Listando tareas vinculadas al evento ID: {evento_id}")
        stmt = select(Tarea).where(Tarea.id_evento == evento_id, Tarea.estado == True)
        result = await db.execute(stmt)
        tareas = result.scalars().all()
        logger.info(f"Se encontraron {len(tareas)} tareas para el evento {evento_id}")
        return tareas
    except Exception as e:
        logger.error(f"Error al listar tareas del evento {evento_id}: {str(e)}")
        raise


async def listar_tareas_por_tipo(db: AsyncSession, tipo_tarea: str, hogar_id: int):
    try:
        logger.info(f"Listando tareas de tipo '{tipo_tarea}' en hogar {hogar_id}")
        # ¡OJO! Su DDL no tiene 'tipo_tarea' en la tabla 'tareas', tiene 'categoria'
        # Voy a asumir que se refería a 'categoria'
        stmt = select(Tarea).where(
            Tarea.categoria == tipo_tarea,  # <-- ¡Cambiado de tipo_tarea a categoria!
            Tarea.id_hogar == hogar_id,
            Tarea.estado == True,
        )
        result = await db.execute(stmt)
        tareas = result.scalars().all()
        logger.info(f"Se encontraron {len(tareas)} tareas de tipo '{tipo_tarea}'")
        return tareas
    except Exception as e:
        logger.error(f"Error al filtrar tareas por tipo '{tipo_tarea}': {str(e)}")
        raise


async def actualizar_estado_tarea(
    db: AsyncSession, tarea_id: int, nuevo_estado: str, miembro_id: int
):
    try:
        logger.info(
            f"Actualizando estado de tarea {tarea_id} a '{nuevo_estado}' por miembro {miembro_id}"
        )
        tarea = await obtener_tarea_por_id(db, tarea_id)
        if not tarea:
            logger.warning(f"No se puede actualizar estado: tarea {tarea_id} no existe")
            raise ValueError(f"Tarea {tarea_id} no existe")

        if tarea.asignado_a != miembro_id and tarea.creado_por != miembro_id:
            logger.warning(
                f"Miembro {miembro_id} no está autorizado para actualizar la tarea {tarea_id}"
            )
            raise ValueError(f"No autorizado para actualizar esta tarea")

        if nuevo_estado not in ["pendiente", "en_progreso", "completada", "cancelada"]:
            logger.error(f"Estado inválido: {nuevo_estado}")
            raise ValueError("Estado de tarea no válido")

        if nuevo_estado == "completada" and tarea.estado_actual != "completada":
            tiempo_seg = int(time.time() - tarea.fecha_asignacion.timestamp())
            tarea.tiempo_total_segundos = tiempo_seg
            logger.info(f"Tarea {tarea_id} completada en {tiempo_seg} segundos")

        tarea.estado_actual = nuevo_estado

        await db.flush()

        logger.info(
            f"Estado de tarea {tarea_id} actualizado (sin commit) a '{nuevo_estado}'"
        )

        if tarea.creado_por and tarea.creado_por != miembro_id:
            notif_data = NotificacionCreate(
                id_miembro_destino=tarea.creado_por,
                id_miembro_origen=miembro_id,
                id_tarea=tarea_id,
                tipo="cambio_estado_tarea",
                mensaje=f"La tarea '{tarea.titulo}' ahora está '{nuevo_estado}'",
            )
            await crear_notificacion(db, notif_data)
            logger.info(
                f"Notificación enviada (sin commit) por cambio de estado en tarea {tarea_id}"
            )

        await db.refresh(tarea)
        return tarea
    except (ValueError, Exception) as e:
        logger.error(f"Error al actualizar estado de tarea {tarea_id}: {str(e)}")
        raise


async def agregar_comentario_a_tarea(
    db: AsyncSession, data: ComentarioTareaCreate, miembro_id: int
):
    try:
        logger.info(f"Agregando comentario a tarea {data.id_tarea}")

        comentario_data = data.model_dump()
        comentario_data["id_miembro"] = miembro_id

        comentario = ComentarioTarea(**comentario_data)
        db.add(comentario)

        await db.flush()
        await db.refresh(comentario)

        tarea = await obtener_tarea_por_id(db, data.id_tarea)
        if tarea:
            id_destino = None
            if tarea.asignado_a == miembro_id and tarea.creado_por:
                id_destino = tarea.creado_por
            elif tarea.creado_por == miembro_id:
                id_destino = tarea.asignado_a

            if id_destino and id_destino != miembro_id:
                notif_data = NotificacionCreate(
                    id_miembro_destino=id_destino,
                    id_miembro_origen=miembro_id,
                    id_tarea=data.id_tarea,
                    tipo="nuevo_comentario",
                    mensaje=f"Hay un nuevo comentario en la tarea '{tarea.titulo}'",
                )
                await crear_notificacion(db, notif_data)
                logger.info(
                    f"Comentario y notificación creados (sin commit) para tarea {data.id_tarea}"
                )
            else:
                logger.info(
                    f"Comentario creado (sin commit) para tarea {data.id_tarea}"
                )
        else:
            logger.warning(f"No se pudo notificar: tarea {data.id_tarea} no encontrada")

        return comentario
    except Exception as e:
        logger.error(f"Error al agregar comentario: {str(e)}")
        raise

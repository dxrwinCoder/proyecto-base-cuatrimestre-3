from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.tarea import Tarea
from models.comentario_tarea import ComentarioTarea
from models.notificacion import Notificacion
import time
from utils.logger import setup_logger

logger = setup_logger("tarea_service")


async def crear_tarea(db: AsyncSession, data: dict):
    try:
        logger.info(f"Creando tarea con datos: {data}")
        tarea = Tarea(**data)
        db.add(tarea)
        await db.commit()
        await db.refresh(tarea)
        logger.info(f"Tarea creada exitosamente con ID: {tarea.id}")
        return tarea
    except Exception as e:
        logger.error(f"Error al crear tarea: {str(e)}")
        await db.rollback()
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
        stmt = select(Tarea).where(
            Tarea.tipo_tarea == tipo_tarea,
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
            return None

        if tarea.asignado_a != miembro_id:
            logger.warning(
                f"Miembro {miembro_id} no está autorizado para actualizar la tarea {tarea_id}"
            )
            return None

        if nuevo_estado not in ["pendiente", "en_progreso", "completada", "cancelada"]:
            logger.error(f"Estado inválido: {nuevo_estado}")
            raise ValueError("Estado de tarea no válido")

        # Registrar tiempo solo si se completa por primera vez
        if nuevo_estado == "completada" and tarea.estado_actual != "completada":
            tiempo_seg = int(time.time() - tarea.fecha_asignacion.timestamp())
            tarea.tiempo_total_segundos = tiempo_seg
            logger.info(f"Tarea {tarea_id} completada en {tiempo_seg} segundos")

        tarea.estado_actual = nuevo_estado
        await db.commit()
        await db.refresh(tarea)
        logger.info(f"Estado de tarea {tarea_id} actualizado a '{nuevo_estado}'")

        # Notificación al creador (quien asignó la tarea)
        notif = Notificacion(
            id_miembro_destino=tarea.asignado_a,  # Ajustar si el creador es diferente
            id_miembro_origen=miembro_id,
            id_tarea=tarea_id,
            tipo="cambio_estado_tarea",
            mensaje=f"La tarea '{tarea.titulo}' ahora está '{nuevo_estado}'",
        )
        db.add(notif)
        await db.commit()
        logger.info(f"Notificación enviada por cambio de estado en tarea {tarea_id}")

        return tarea
    except Exception as e:
        logger.error(f"Error al actualizar estado de tarea {tarea_id}: {str(e)}")
        await db.rollback()
        raise


async def agregar_comentario_a_tarea(db: AsyncSession, data: dict):
    try:
        logger.info(f"Agregando comentario a tarea {data.get('id_tarea')}")
        comentario = ComentarioTarea(**data)
        db.add(comentario)
        await db.commit()
        await db.refresh(comentario)

        # Notificar al asignado
        tarea = await obtener_tarea_por_id(db, data["id_tarea"])
        if tarea:
            notif = Notificacion(
                id_miembro_destino=tarea.asignado_a,
                id_miembro_origen=data["id_miembro"],
                id_tarea=data["id_tarea"],
                tipo="nuevo_comentario",
                mensaje="Se agregó un comentario a la tarea",
            )
            db.add(notif)
            await db.commit()
            logger.info(
                f"Comentario y notificación creados para tarea {data['id_tarea']}"
            )
        else:
            logger.warning(
                f"No se pudo notificar: tarea {data['id_tarea']} no encontrada"
            )

        return comentario
    except Exception as e:
        logger.error(f"Error al agregar comentario: {str(e)}")
        await db.rollback()
        raise

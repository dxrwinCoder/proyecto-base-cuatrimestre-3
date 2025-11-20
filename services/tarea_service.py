from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from models.tarea import Tarea
from models.comentario_tarea import ComentarioTarea
from models.miembro import Miembro
from models.evento import Evento
import time
from utils.logger import setup_logger
from datetime import datetime, timedelta, date
from services.notificacion_service import crear_notificacion
from services.evento_service import notificar_si_evento_completado
import os
from uuid import uuid4
from fastapi import UploadFile
import base64
from schemas.notificacion import NotificacionCreate
from schemas.tarea import TareaCreate  # ¡Asumiendo que tiene TareaCreate!
from schemas.comentario_tarea import (
    ComentarioTareaCreate,
)

logger = setup_logger("tarea_service")


async def crear_tarea(db: AsyncSession, data: TareaCreate, creador_id: int):
    try:
        logger.info(f"Creando tarea con datos: {data.titulo}")

        tarea_data = data.dict()
        tarea_data["creado_por"] = creador_id

        tarea = Tarea(**tarea_data)
        db.add(tarea)

        await db.flush()
        await db.refresh(tarea)

        # 1. Ejecutar consulta de carga ansiosa (joinedload)
        stmt_select = (
            select(Tarea).where(Tarea.id == tarea.id)
            # --- (Añadir joinedload para la relación) ---
            .options(joinedload(Tarea.comentarios))
        )
        result_loaded = await db.execute(stmt_select)

        # 2. Aplicar .unique() (necesario para colecciones joinedload) y obtener el escalar
        tarea_cargada = result_loaded.unique().scalar_one()

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

        # return tarea
        return tarea_cargada
    except Exception as e:
        logger.error(f"Error al crear tarea: {str(e)}")
        raise


async def obtener_tarea_por_id(db: AsyncSession, tarea_id: int):
    try:
        logger.info(f"Buscando tarea con ID: {tarea_id}")
        stmt = (
            select(Tarea)
            .where(Tarea.id == tarea_id)
            .options(joinedload(Tarea.comentarios))
        )
        result = await db.execute(stmt)
        tarea = result.unique().scalar_one_or_none()
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
        stmt = (
            select(Tarea)
            .where(Tarea.asignado_a == miembro_id, Tarea.estado == True)
            .options(joinedload(Tarea.comentarios))
        )
        result = await db.execute(stmt)
        tareas = result.unique().scalars().all()
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

        # Si la tarea pertenece a un evento, verificar si todas las tareas están completadas
        if tarea.id_evento:
            await notificar_si_evento_completado(db, tarea.id_evento)

        # Evitar lazy-load en la respuesta: recargar con comentarios en modo eager
        stmt = (
            select(Tarea)
            .where(Tarea.id == tarea_id)
            .options(joinedload(Tarea.comentarios))
        )
        loaded = (await db.execute(stmt)).unique().scalar_one()
        return loaded
    except (ValueError, Exception) as e:
        logger.error(f"Error al actualizar estado de tarea {tarea_id}: {str(e)}")
        raise


async def agregar_comentario_a_tarea(
    db: AsyncSession, data: ComentarioTareaCreate, miembro_id: int
):
    try:
        logger.info(f"Agregando comentario a tarea {data.id_tarea}")

        comentario_data = data.dict()
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


async def agregar_comentario_con_imagen(
    db: AsyncSession,
    tarea_id: int,
    miembro_id: int,
    contenido: str | None,
    archivo: UploadFile | None,
    media_root: str,
):
    """
    Agrega un comentario con imagen a una tarea. Guarda el archivo en disco y persiste la ruta.
    """
    try:
        logger.info(f"Agregando comentario con imagen a tarea {tarea_id}")
        tarea = await obtener_tarea_por_id(db, tarea_id)
        if not tarea:
            raise ValueError("Tarea no encontrada")

        if not archivo:
            raise ValueError("No se adjuntó archivo.")

        os.makedirs(media_root, exist_ok=True)
        ext = os.path.splitext(archivo.filename)[1] or ".bin"
        nombre = f"{uuid4().hex}{ext}"
        ruta_archivo = os.path.join(media_root, nombre)
        contenido_bytes = await archivo.read()
        with open(ruta_archivo, "wb") as f:
            f.write(contenido_bytes)
        # Guardamos en BD la ruta absoluta/relativa del archivo almacenado
        ruta_imagen = ruta_archivo

        comentario = ComentarioTarea(
            id_tarea=tarea_id,
            id_miembro=miembro_id,
            contenido=contenido or "",
            url_imagen=ruta_imagen,
        )
        db.add(comentario)
        await db.flush()
        await db.refresh(comentario)
        return comentario
    except Exception as e:
        logger.error(f"Error al agregar comentario con imagen: {str(e)}")
        raise


async def listar_comentarios_por_tarea(db: AsyncSession, tarea_id: int):
    """
    Devuelve comentarios activos para la tarea dada, ordenados por creación.
    Se mantiene sin commit para que la ruta decida el control transaccional.
    """
    try:
        stmt = (
            select(ComentarioTarea)
            .where(ComentarioTarea.id_tarea == tarea_id, ComentarioTarea.estado == True)
            .order_by(ComentarioTarea.fecha_creacion.asc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error al listar comentarios de la tarea {tarea_id}: {str(e)}")
        raise


async def asignar_tarea_a_evento(db: AsyncSession, tarea_id: int, evento_id: int):
    """
    Vincula una tarea existente a un evento y notifica al asignado.
    """
    tarea = await db.get(Tarea, tarea_id)
    evento = await db.get(Evento, evento_id)
    if not tarea or not tarea.estado:
        raise ValueError("Tarea no encontrada o inactiva")
    if not evento or not evento.estado:
        raise ValueError("Evento no encontrado o inactivo")

    tarea.id_evento = evento_id
    await db.flush()

    # Notificar al asignado
    if tarea.asignado_a:
        notif_data = NotificacionCreate(
            id_miembro_destino=tarea.asignado_a,
            id_miembro_origen=evento.creado_por,
            id_tarea=tarea.id,
            id_evento=evento_id,
            tipo="tarea_asignada_evento",
            mensaje=f"Se te asignó la tarea '{tarea.titulo}' en el evento '{evento.titulo}'",
        )
        await crear_notificacion(db, notif_data)

    return tarea


async def reasignar_miembro_tarea_evento(
    db: AsyncSession, tarea_id: int, evento_id: int, nuevo_miembro_id: int, actor_id: int
):
    """
    Reasigna un miembro a una tarea que pertenece a un evento.
    """
    tarea = await db.get(Tarea, tarea_id)
    if not tarea or not tarea.estado or tarea.id_evento != evento_id:
        raise ValueError("La tarea no pertenece al evento o está inactiva")

    tarea.asignado_a = nuevo_miembro_id
    await db.flush()

    notif_data = NotificacionCreate(
        id_miembro_destino=nuevo_miembro_id,
        id_miembro_origen=actor_id,
        id_tarea=tarea.id,
        id_evento=evento_id,
        tipo="tarea_reasignada",
        mensaje=f"Se te reasignó la tarea '{tarea.titulo}' del evento.",
    )
    await crear_notificacion(db, notif_data)
    return tarea


# Listar TODAS las tareas del hogar (con comentarios para el req. 6)
async def listar_todas_tareas_hogar(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Admin listando TODAS las tareas del hogar {hogar_id}")
        stmt = (
            select(Tarea)
            .where(Tarea.id_hogar == hogar_id, Tarea.estado == True)
            .options(joinedload(Tarea.comentarios))  # Carga comentarios (Req. 6)
            .order_by(Tarea.fecha_creacion.desc())
        )
        result = await db.execute(stmt)
        return result.unique().scalars().all()
    except Exception as e:
        logger.error(f"Error al listar todas las tareas del hogar: {str(e)}")
        raise


# Listar tareas asignadas POR el administrador (creado_por)
async def listar_tareas_creadas_por_mi(db: AsyncSession, admin_id: int):
    try:
        logger.info(f"Listando tareas creadas por Admin ID: {admin_id}")
        stmt = (
            select(Tarea)
            .where(
                Tarea.creado_por == admin_id,
                Tarea.estado == True,  # Activas (no borradas)
                # Opcional: Si "activas" significa "no completadas", añadir:
                # Tarea.estado_actual != 'completada'
            )
            .options(joinedload(Tarea.miembro_asignado))  # Ver a quién se asignó
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error al listar tareas creadas por admin: {str(e)}")
        raise


# Listar tareas próximas a vencer (Filtro Manual)
async def listar_tareas_proximas_a_vencer(
    db: AsyncSession, hogar_id: int, fecha_limite: datetime
):
    try:
        logger.info(f"Buscando tareas que vencen antes de: {fecha_limite}")
        stmt = (
            select(Tarea)
            .where(
                Tarea.id_hogar == hogar_id,
                Tarea.estado_actual != "completada",  # Solo pendientes/progreso
                Tarea.fecha_limite <= fecha_limite,  # Filtro de fecha
                Tarea.fecha_limite
                >= datetime.now().date(),  # Que no estén vencidas ya (opcional)
            )
            .order_by(Tarea.fecha_limite.asc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error al filtrar tareas por vencimiento: {str(e)}")
        raise


# Listar tareas en estado "En Progreso"
async def listar_tareas_en_proceso(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Listando tareas en proceso del hogar {hogar_id}")
        stmt = (
            select(Tarea)
            .where(Tarea.id_hogar == hogar_id, Tarea.estado_actual == "en_progreso")
            .options(joinedload(Tarea.miembro_asignado))
        )

        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error al listar tareas en proceso: {str(e)}")
        raise

from datetime import datetime, timedelta
import calendar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from models.evento import Evento
from models.tarea import Tarea
from models.miembro import Miembro
from schemas.notificacion import NotificacionCreate
from services.notificacion_service import crear_notificacion


async def crear_evento(db: AsyncSession, data: dict):
    """
    Crea un evento y deja el commit pendiente para quien llame.
    Esto permite agrupar operaciones (ej. crear evento + tareas) en una transacción.
    """
    evento = Evento(**data)
    db.add(evento)
    await db.flush()
    await db.refresh(evento)
    return evento


async def listar_eventos_por_hogar(db: AsyncSession, hogar_id: int):
    stmt = select(Evento).where(Evento.id_hogar == hogar_id, Evento.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()


async def listar_eventos_activos(db: AsyncSession, hogar_id: int):
    """
    Eventos activos (estado=True) del hogar.
    """
    stmt = select(Evento).where(
        Evento.id_hogar == hogar_id,
        Evento.estado == True,
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def listar_eventos_en_mes_actual(db: AsyncSession, hogar_id: int):
    """
    Eventos activos cuyo datetime cae dentro del mes actual del sistema.
    """
    hoy = datetime.now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    _, last_day = calendar.monthrange(hoy.year, hoy.month)
    fin_mes = inicio_mes.replace(day=last_day, hour=23, minute=59, second=59)

    stmt = select(Evento).where(
        Evento.id_hogar == hogar_id,
        Evento.estado == True,
        Evento.fecha_hora >= inicio_mes,
        Evento.fecha_hora <= fin_mes,
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def obtener_evento(db: AsyncSession, evento_id: int):
    stmt = select(Evento).where(Evento.id == evento_id, Evento.estado == True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def listar_tareas_de_evento(db: AsyncSession, evento_id: int):
    stmt = select(Tarea).where(Tarea.id_evento == evento_id, Tarea.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()


async def listar_eventos_asignados_a_miembro(db: AsyncSession, miembro_id: int):
    """
    Eventos donde el miembro tiene al menos una tarea asignada y el evento está activo.
    """
    stmt = (
        select(Evento)
        .join(Tarea, Tarea.id_evento == Evento.id)
        .where(Evento.estado == True, Tarea.estado == True, Tarea.asignado_a == miembro_id)
        .distinct()
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def listar_eventos_asignados_en_mes_actual(db: AsyncSession, miembro_id: int):
    hoy = datetime.now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    _, last_day = calendar.monthrange(hoy.year, hoy.month)
    fin_mes = inicio_mes.replace(day=last_day, hour=23, minute=59, second=59)

    stmt = (
        select(Evento)
        .join(Tarea, Tarea.id_evento == Evento.id)
        .where(
            Evento.estado == True,
            Tarea.estado == True,
            Tarea.asignado_a == miembro_id,
            Evento.fecha_hora >= inicio_mes,
            Evento.fecha_hora <= fin_mes,
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def listar_eventos_asignados_en_semana_actual(db: AsyncSession, miembro_id: int):
    hoy = datetime.now()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_semana = inicio_semana + timedelta(days=6, hours=23, minutes=59, seconds=59)

    stmt = (
        select(Evento)
        .join(Tarea, Tarea.id_evento == Evento.id)
        .where(
            Evento.estado == True,
            Tarea.estado == True,
            Tarea.asignado_a == miembro_id,
            Evento.fecha_hora >= inicio_semana,
            Evento.fecha_hora <= fin_semana,
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def listar_tareas_de_evento_por_estado(
    db: AsyncSession, evento_id: int, estado_actual: str
):
    stmt = select(Tarea).where(
        Tarea.id_evento == evento_id,
        Tarea.estado == True,
        Tarea.estado_actual == estado_actual,
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def miembros_relacionados_a_evento(db: AsyncSession, evento_id: int):
    """
    Miembros que participan en el evento: creador y asignados a tareas del evento.
    """
    tareas_stmt = select(Tarea.asignado_a).where(Tarea.id_evento == evento_id)
    asignados_ids = (await db.execute(tareas_stmt)).scalars().all()
    ids_unicos = set(asignados_ids)

    evento = await db.get(Evento, evento_id)
    if evento and evento.creado_por:
        ids_unicos.add(evento.creado_por)

    if not ids_unicos:
        return []

    miembros_stmt = select(Miembro).where(
        Miembro.id.in_(ids_unicos), Miembro.estado == True
    )
    result = await db.execute(miembros_stmt)
    return result.scalars().all()


async def quitar_tarea_de_evento(db: AsyncSession, evento_id: int, tarea_id: int):
    """
    Desasocia una tarea de un evento (set id_evento a NULL).
    """
    tarea = await db.get(Tarea, tarea_id)
    if not tarea or tarea.id_evento != evento_id:
        return None
    tarea.id_evento = None
    await db.flush()
    await db.refresh(tarea)
    return tarea


async def notificar_si_evento_completado(db: AsyncSession, evento_id: int):
    """
    Si todas las tareas del evento están en estado 'completada', notifica al creador.
    """
    evento = await db.get(Evento, evento_id)
    if not evento:
        return

    pendientes_stmt = select(func.count(Tarea.id)).where(
        Tarea.id_evento == evento_id,
        Tarea.estado == True,
        Tarea.estado_actual != "completada",
    )
    pendientes = (await db.execute(pendientes_stmt)).scalar_one()

    if pendientes == 0 and evento.creado_por:
        notif_data = NotificacionCreate(
            id_miembro_destino=evento.creado_por,
            id_miembro_origen=evento.creado_por,
            id_tarea=None,
            id_evento=evento_id,
            tipo="evento_completado",
            mensaje=f"Todas las tareas del evento '{evento.titulo}' están completadas.",
        )
        await crear_notificacion(db, notif_data)

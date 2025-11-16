# services/ranking_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta

from models.estadisticas_semanales import EstadisticaSemanal
from models.miembro import Miembro
from models.tarea import Tarea  # Necesario para el cálculo del robot
from utils.logger import setup_logger

logger = setup_logger("ranking_service")


async def obtener_ranking_hogar(db: AsyncSession, hogar_id: int) -> list[dict]:
    """
    Obtiene el ranking de la semana actual para un hogar.
    Devuelve una lista de diccionarios que contienen el objeto Miembro
    y el conteo de tareas.
    """
    try:
        logger.info(f"Obteniendo ranking semanal para el hogar ID: {hogar_id}")

        # 1. Obtener el lunes de esta semana (inicio_semana)
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday())

        # 2. Consultar la tabla de estadísticas
        stmt = (
            select(Miembro, EstadisticaSemanal.tareas_completadas)
            .join(EstadisticaSemanal, Miembro.id == EstadisticaSemanal.id_miembro)
            .where(
                Miembro.id_hogar == hogar_id,
                Miembro.estado == True,
                EstadisticaSemanal.inicio_semana == inicio_semana,
            )
            .order_by(EstadisticaSemanal.tareas_completadas.desc())
            # Cargar la relación 'rol' para evitar N+1 en el schema MiembroResponse
            .options(joinedload(Miembro.rol))
        )

        result = await db.execute(stmt)

        # 3. Formatear la respuesta
        ranking = []
        for miembro, tareas_count in result.all():
            ranking.append({"miembro": miembro, "tareas_completadas": tareas_count})

        return ranking
    except Exception as e:
        logger.error(f"Error al obtener ranking del hogar {hogar_id}: {str(e)}")
        raise


async def calcular_ranking_semanal(db: AsyncSession, hogar_id: int):
    """
    ¡EL ROBOT!
    Calcula las tareas completadas de la semana PASADA y las guarda.
    Esta función NO debe ser llamada por una ruta, sino por un scheduler (APScheduler).
    """
    try:
        logger.info(f"Calculando ranking de semana pasada para hogar ID: {hogar_id}")

        # 1. Obtener fechas de la semana PASADA
        hoy = datetime.now().date()
        # (ej. si hoy es Lunes, queremos del Lunes pasado al Domingo pasado)
        fin_semana_pasada = hoy - timedelta(days=hoy.weekday() + 1)
        inicio_semana_pasada = fin_semana_pasada - timedelta(days=6)

        logger.info(
            f"Calculando para el período: {inicio_semana_pasada} a {fin_semana_pasada}"
        )

        # 2. Query: Contar tareas completadas por miembro en ese período
        stmt_conteo = (
            select(Tarea.asignado_a, func.count(Tarea.id).label("total_completadas"))
            .where(
                Tarea.id_hogar == hogar_id,
                Tarea.estado_actual == "completada",
                # Asumiendo que fecha_actualizacion guarda cuándo se completó
                func.date(Tarea.fecha_actualizacion).between(
                    inicio_semana_pasada, fin_semana_pasada
                ),
            )
            .group_by(Tarea.asignado_a)
        )

        result_conteo = await db.execute(stmt_conteo)
        # Crear un diccionario de conteo para acceso rápido: {miembro_id: conteo}
        conteo_dict = {row.asignado_a: row.total_completadas for row in result_conteo}

        # 3. Insertar/Actualizar en la tabla de estadísticas
        miembros_stmt = select(Miembro).where(
            Miembro.id_hogar == hogar_id, Miembro.estado == True
        )
        miembros = (await db.execute(miembros_stmt)).scalars().all()

        stats_guardadas = []
        for miembro in miembros:
            total = conteo_dict.get(
                miembro.id, 0
            )  # Obtener conteo, 0 si no hizo tareas

            # Buscar si ya existe un registro para esa semana
            stat_existente = await db.get(
                EstadisticaSemanal, (miembro.id, inicio_semana_pasada)
            )

            if stat_existente:
                stat_existente.tareas_completadas = total
            else:
                stat_existente = EstadisticaSemanal(
                    id_miembro=miembro.id,
                    inicio_semana=inicio_semana_pasada,
                    tareas_completadas=total,
                )
                db.add(stat_existente)

            stats_guardadas.append(stat_existente)

        # ¡Este servicio SÍ hace commit porque es un "robot" (proceso batch)!
        await db.commit()
        logger.info(
            f"Ranking de semana pasada para hogar {hogar_id} calculado y guardado."
        )
        return stats_guardadas

    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error al calcular ranking semanal para hogar {hogar_id}: {str(e)}"
        )
        raise

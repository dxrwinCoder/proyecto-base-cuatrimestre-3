from sqlalchemy.ext.asyncio import AsyncSession
from models.tarea import Tarea
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import setup_logger

logger = setup_logger("tarea_service")


async def crear_tarea(db: AsyncSession, data: dict):
    try:
        logger.info(f"Creando nueva tarea: {data.get('titulo', 'Sin título')}")
        tarea = Tarea(**data)
        db.add(tarea)
        await db.commit()
        await db.refresh(tarea)
        logger.info(f"Tarea creada exitosamente: {tarea.id}")
        return tarea
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al crear tarea: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear tarea: {str(e)}")
        await db.rollback()
        raise


async def listar_tareas_por_hogar(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Listando tareas para el hogar: {hogar_id}")
        from sqlalchemy import select

        stmt = select(Tarea).where(Tarea.id_hogar == hogar_id, Tarea.estado == True)
        result = await db.execute(stmt)
        tareas = result.scalars().all()
        logger.info(f"Se encontraron {len(tareas)} tareas activas")
        return tareas
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al listar tareas: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al listar tareas: {str(e)}")
        raise


async def marcar_completada(db: AsyncSession, tarea_id: int):
    try:
        logger.info(f"Marcando tarea como completada: {tarea_id}")
        tarea = await db.get(Tarea, tarea_id)

        if not tarea:
            logger.warning(f"Tarea no encontrada: {tarea_id}")
            return None

        if not tarea.estado:
            logger.warning(f"Tarea ya está desactivada: {tarea_id}")
            return None

        tarea.estado_tarea = "completada"
        await db.commit()
        logger.info(f"Tarea marcada como completada exitosamente: {tarea_id}")
        return tarea
    except SQLAlchemyError as e:
        logger.error(
            f"Error de base de datos al marcar tarea como completada: {str(e)}"
        )
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al marcar tarea como completada: {str(e)}")
        await db.rollback()
        raise


async def eliminar_tarea_logico(db: AsyncSession, tarea_id: int):
    try:
        logger.info(f"Eliminando tarea (lógico): {tarea_id}")
        tarea = await db.get(Tarea, tarea_id)

        if not tarea:
            logger.warning(f"Tarea no encontrada para eliminar: {tarea_id}")
            return False

        if not tarea.estado:
            logger.warning(f"Tarea ya está desactivada: {tarea_id}")
            return False

        tarea.estado = False
        await db.commit()
        logger.info(f"Tarea eliminada lógicamente: {tarea_id}")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al eliminar tarea: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al eliminar tarea: {str(e)}")
        await db.rollback()
        raise

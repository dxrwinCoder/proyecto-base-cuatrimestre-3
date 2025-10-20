
from sqlalchemy.ext.asyncio import AsyncSession
from models.hogar import Hogar
from utils.logger import setup_logger
from sqlalchemy.exc import SQLAlchemyError

logger = setup_logger("hogar_service")

async def crear_hogar(db: AsyncSession, nombre: str):
    try:
        logger.info(f"Creando hogar con nombre: {nombre}")
        hogar = Hogar(nombre=nombre)
        db.add(hogar)
        await db.commit()
        await db.refresh(hogar)
        logger.info(f"Hogar creado exitosamente: {hogar.nombre}")
        return hogar
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al crear hogar: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear hogar: {str(e)}")
        await db.rollback()
        raise

async def obtener_hogar(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Obteniendo hogar con ID: {hogar_id}")
        hogar = await db.get(Hogar, hogar_id)
        if hogar:
            logger.info(f"Hogar encontrado: {hogar.nombre}")
        else:
            logger.warning(f"No se encontró hogar con ID: {hogar_id}")
        return hogar
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al obtener hogar: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener hogar: {str(e)}")
        raise

async def listar_hogares_activos(db: AsyncSession):
    from sqlalchemy import select
    try:
        logger.info("Listando hogares activos")
        stmt = select(Hogar).where(Hogar.estado == True)
        result = await db.execute(stmt)
        hogares = result.scalars().all()
        logger.info(f"Se encontraron {len(hogares)} hogares activos")
        return hogares
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al listar hogares: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al listar hogares: {str(e)}")
        raise

async def actualizar_hogar(db: AsyncSession, hogar_id: int, nombre: str):
    try:
        logger.info(f"Actualizando hogar con ID: {hogar_id}")
        hogar = await db.get(Hogar, hogar_id)
        if hogar and hogar.estado:
            hogar.nombre = nombre
            await db.commit()
            logger.info(f"Hogar actualizado exitosamente: {hogar.nombre}")
            return hogar
        logger.warning(f"No se pudo actualizar hogar con ID: {hogar_id}")
        return None
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al actualizar hogar: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al actualizar hogar: {str(e)}")
        await db.rollback()
        raise

async def eliminar_hogar_logico(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Eliminando (lógico) hogar con ID: {hogar_id}")
        hogar = await db.get(Hogar, hogar_id)
        if hogar and hogar.estado:
            hogar.estado = False
            await db.commit()
            logger.info(f"Hogar eliminado lógicamente: {hogar_id}")
            return True
        logger.warning(f"No se pudo eliminar hogar con ID: {hogar_id}")
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al eliminar hogar: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al eliminar hogar: {str(e)}")
        await db.rollback()
        raise
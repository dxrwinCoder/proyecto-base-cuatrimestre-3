from sqlalchemy.ext.asyncio import AsyncSession
from models.rol import Rol
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import setup_logger

logger = setup_logger("rol_service")


async def crear_rol(db: AsyncSession, nombre: str, descripcion: str = ""):
    try:
        logger.info(f"Creando nuevo rol: {nombre}")
        rol = Rol(nombre=nombre, descripcion=descripcion)
        db.add(rol)
        await db.commit()
        await db.refresh(rol)
        logger.info(f"Rol creado exitosamente: {rol.id}")
        return rol
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al crear rol: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear rol: {str(e)}")
        await db.rollback()
        raise


async def obtener_rol(db: AsyncSession, rol_id: int):
    try:
        logger.info(f"Buscando rol con ID: {rol_id}")
        rol = await db.get(Rol, rol_id)

        if rol:
            logger.info(f"Rol encontrado: {rol.nombre}")
        else:
            logger.warning(f"Rol no encontrado con ID: {rol_id}")

        return rol
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al obtener rol: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener rol: {str(e)}")
        raise

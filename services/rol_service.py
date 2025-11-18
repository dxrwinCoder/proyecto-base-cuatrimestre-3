# refactorizacion por gemini pro

from sqlalchemy.ext.asyncio import AsyncSession
from models.rol import Rol
from schemas.rol import RolCreate, RolUpdate  # <-- ¡Importar schemas!
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import setup_logger
from sqlalchemy import select  # <-- Importar select

logger = setup_logger("rol_service")


async def crear_rol(db: AsyncSession, rol_data: RolCreate):  # <-- ¡Recibe schema!
    try:
        # --- ¡Lógica de validación añadida! ---
        stmt = select(Rol).where(Rol.nombre == rol_data.nombre)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            logger.warning(
                f"Intento de crear rol con nombre duplicado: {rol_data.nombre}"
            )
            raise ValueError("El nombre del rol ya existe")
        # --- Fin de la validación ---

        logger.info(f"Creando nuevo rol: {rol_data.nombre}")

        rol = Rol(**rol_data.dict())
        db.add(rol)

        await db.flush()  # <-- ¡CAMBIO! de commit a flush
        await db.refresh(rol)

        logger.info(f"Rol creado (sin commit): {rol.id}")
        return rol
    except (SQLAlchemyError, ValueError) as e:
        logger.error(f"Error de base de datos al crear rol: {str(e)}")
        raise  # Relanzamos el error para que la ruta haga rollback


# (Dejamos los otros servicios como están, ya que no hacen commit)
async def obtener_rol(db: AsyncSession, rol_id: int):
    try:
        logger.info(f"Buscando rol con ID: {rol_id}")

        # --- ¡ESTA ES LA LÓGICA QUE FALTABA! ---
        rol = await db.get(Rol, rol_id)
        if rol:
            logger.info(f"Rol encontrado: {rol.nombre}")
        else:
            logger.warning(f"Rol no encontrado con ID: {rol_id}")
        return rol
        # --- FIN DEL ARREGLO ---

    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al obtener rol: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener rol: {str(e)}")
        raise


# from sqlalchemy.ext.asyncio import AsyncSession
# from models.rol import Rol
# from sqlalchemy.exc import SQLAlchemyError
# from utils.logger import setup_logger

# logger = setup_logger("rol_service")


# async def crear_rol(db: AsyncSession, nombre: str, descripcion: str = ""):
#     try:
#         logger.info(f"Creando nuevo rol: {nombre}")
#         rol = Rol(nombre=nombre, descripcion=descripcion)
#         db.add(rol)
#         await db.commit()
#         await db.refresh(rol)
#         logger.info(f"Rol creado exitosamente: {rol.id}")
#         return rol
#     except SQLAlchemyError as e:
#         logger.error(f"Error de base de datos al crear rol: {str(e)}")
#         await db.rollback()
#         raise
#     except Exception as e:
#         logger.error(f"Error inesperado al crear rol: {str(e)}")
#         await db.rollback()
#         raise


# async def obtener_rol(db: AsyncSession, rol_id: int):
#     try:
#         logger.info(f"Buscando rol con ID: {rol_id}")
#         rol = await db.get(Rol, rol_id)

#         if rol:
#             logger.info(f"Rol encontrado: {rol.nombre}")
#         else:
#             logger.warning(f"Rol no encontrado con ID: {rol_id}")

#         return rol
#     except SQLAlchemyError as e:
#         logger.error(f"Error de base de datos al obtener rol: {str(e)}")
#         raise
#     except Exception as e:
#         logger.error(f"Error inesperado al obtener rol: {str(e)}")
#         raise

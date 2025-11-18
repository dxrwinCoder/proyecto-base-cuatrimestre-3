# refactorizacion por gemini pro

# services/hogar_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from models.hogar import Hogar
from schemas.hogar import HogarCreate, HogarUpdate  # <-- ¡Importar schemas!
from utils.logger import setup_logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select  # <-- Importar select

logger = setup_logger("hogar_service")


async def crear_hogar(db: AsyncSession, hogar_data: HogarCreate):  # <-- ¡Recibe schema!
    try:
        # --- ¡Validación añadida! ---
        stmt = select(Hogar).where(Hogar.nombre == hogar_data.nombre)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            logger.warning(
                f"Intento de crear hogar con nombre duplicado: {hogar_data.nombre}"
            )
            raise ValueError("El nombre del hogar ya existe")
        # --- Fin de la validación ---

        logger.info(f"Creando hogar con nombre: {hogar_data.nombre}")
        hogar = Hogar(**hogar_data.dict())
        db.add(hogar)

        await db.flush()  # <-- ¡CAMBIO! de commit a flush
        await db.refresh(hogar)

        logger.info(f"Hogar creado (sin commit): {hogar.nombre}")
        return hogar
    except (SQLAlchemyError, ValueError) as e:
        logger.error(f"Error de base de datos al crear hogar: {str(e)}")
        raise  # Relanzar para que la ruta haga rollback


async def obtener_hogar(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Obteniendo hogar con ID: {hogar_id}")

        # --- ¡ESTA ES LA LÓGICA QUE FALTABA! ---
        hogar = await db.get(Hogar, hogar_id)
        if hogar:
            logger.info(f"Hogar encontrado: {hogar.nombre}")
        else:
            logger.warning(f"No se encontró hogar con ID: {hogar_id}")
        return hogar
        # --- FIN DEL ARREGLO ---

    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al obtener hogar: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener hogar: {str(e)}")
        raise


async def listar_hogares_activos(db: AsyncSession):
    try:
        logger.info("Listando hogares activos")

        # --- ¡ESTA ES LA LÓGICA QUE FALTABA! ---
        stmt = select(Hogar).where(Hogar.estado == True)
        result = await db.execute(stmt)
        hogares = result.scalars().all()
        logger.info(f"Se encontraron {len(hogares)} hogares activos")
        return hogares
        # --- FIN DEL ARREGLO ---

    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al listar hogares: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al listar hogares: {str(e)}")
        raise


async def actualizar_hogar(
    db: AsyncSession, hogar_id: int, hogar_data: HogarUpdate
):  # <-- ¡Recibe schema!
    try:
        logger.info(f"Actualizando hogar con ID: {hogar_id}")
        hogar = await db.get(Hogar, hogar_id)

        if not hogar or not hogar.estado:
            logger.warning(f"No se pudo actualizar hogar con ID: {hogar_id}")
            return None

        # Actualizar solo los campos enviados
        update_data = hogar_data.dict()(exclude_unset=True)
        for key, value in update_data.items():
            setattr(hogar, key, value)

        await db.flush()  # <-- ¡CAMBIO! de commit a flush
        await db.refresh(hogar)

        logger.info(f"Hogar actualizado (sin commit): {hogar.nombre}")
        return hogar
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al actualizar hogar: {str(e)}")
        raise


async def eliminar_hogar_logico(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Eliminando (lógico) hogar con ID: {hogar_id}")
        hogar = await db.get(Hogar, hogar_id)

        if not hogar or not hogar.estado:
            logger.warning(f"No se pudo eliminar hogar con ID: {hogar_id}")
            return False

        hogar.estado = False

        await db.flush()  # <-- ¡CAMBIO! de commit a flush

        logger.info(f"Hogar eliminado lógicamente (sin commit): {hogar_id}")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al eliminar hogar: {str(e)}")
        raise


async def _validar_nombre_hogar_duplicado(db: AsyncSession, nombre: str):
    stmt = select(Hogar).where(Hogar.nombre == nombre)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        logger.warning(f"Intento de crear hogar con nombre duplicado: {nombre}")
        raise ValueError("El nombre del hogar ya existe")


# --- ¡NUEVA FUNCIÓN INTERNA PARA EL SERVICIO DE AUTH! ---
async def crear_hogar_interno(db: AsyncSession, nombre_hogar: str) -> Hogar:
    """
    Función interna para ser llamada por otros servicios (ej. auth_service)
    sin necesidad de pasar un schema Pydantic.
    """
    await _validar_nombre_hogar_duplicado(db, nombre_hogar)

    logger.info(f"Creando hogar (interno) con nombre: {nombre_hogar}")
    hogar = Hogar(nombre=nombre_hogar)
    db.add(hogar)
    await db.flush()
    await db.refresh(hogar)
    logger.info(f"Hogar (interno) creado (sin commit): {hogar.nombre}")
    return hogar


async def crear_hogar_interno(db: AsyncSession, nombre_hogar: str) -> Hogar:
    """
    Función interna para ser llamada por otros servicios (ej. auth_service)
    sin necesidad de pasar un schema.
    """
    try:
        await _validar_nombre_hogar_duplicado(db, nombre_hogar)
        logger.info(f"Creando hogar (interno) con nombre: {nombre_hogar}")
        hogar = Hogar(nombre=nombre_hogar)
        db.add(hogar)
        await db.flush()
        await db.refresh(hogar)
        logger.info(f"Hogar (interno) creado (sin commit): {hogar.nombre}")
        return hogar
    except (SQLAlchemyError, ValueError) as e:
        logger.error(f"Error de base de datos al crear hogar interno: {str(e)}")
        raise


# --- FIN DE LA NUEVA FUNCIÓN ---
# from sqlalchemy.ext.asyncio import AsyncSession
# from models.hogar import Hogar
# from utils.logger import setup_logger
# from sqlalchemy.exc import SQLAlchemyError

# logger = setup_logger("hogar_service")

# async def crear_hogar(db: AsyncSession, nombre: str):
#     try:
#         logger.info(f"Creando hogar con nombre: {nombre}")
#         hogar = Hogar(nombre=nombre)
#         db.add(hogar)
#         await db.commit()
#         await db.refresh(hogar)
#         logger.info(f"Hogar creado exitosamente: {hogar.nombre}")
#         return hogar
#     except SQLAlchemyError as e:
#         logger.error(f"Error de base de datos al crear hogar: {str(e)}")
#         await db.rollback()
#         raise
#     except Exception as e:
#         logger.error(f"Error inesperado al crear hogar: {str(e)}")
#         await db.rollback()
#         raise

# async def obtener_hogar(db: AsyncSession, hogar_id: int):
#     try:
#         logger.info(f"Obteniendo hogar con ID: {hogar_id}")
#         hogar = await db.get(Hogar, hogar_id)
#         if hogar:
#             logger.info(f"Hogar encontrado: {hogar.nombre}")
#         else:
#             logger.warning(f"No se encontró hogar con ID: {hogar_id}")
#         return hogar
#     except SQLAlchemyError as e:
#         logger.error(f"Error de base de datos al obtener hogar: {str(e)}")
#         raise
#     except Exception as e:
#         logger.error(f"Error inesperado al obtener hogar: {str(e)}")
#         raise

# async def listar_hogares_activos(db: AsyncSession):
#     from sqlalchemy import select
#     try:
#         logger.info("Listando hogares activos")
#         stmt = select(Hogar).where(Hogar.estado == True)
#         result = await db.execute(stmt)
#         hogares = result.scalars().all()
#         logger.info(f"Se encontraron {len(hogares)} hogares activos")
#         return hogares
#     except SQLAlchemyError as e:
#         logger.error(f"Error de base de datos al listar hogares: {str(e)}")
#         raise
#     except Exception as e:
#         logger.error(f"Error inesperado al listar hogares: {str(e)}")
#         raise

# async def actualizar_hogar(db: AsyncSession, hogar_id: int, nombre: str):
#     try:
#         logger.info(f"Actualizando hogar con ID: {hogar_id}")
#         hogar = await db.get(Hogar, hogar_id)
#         if hogar and hogar.estado:
#             hogar.nombre = nombre
#             await db.commit()
#             logger.info(f"Hogar actualizado exitosamente: {hogar.nombre}")
#             return hogar
#         logger.warning(f"No se pudo actualizar hogar con ID: {hogar_id}")
#         return None
#     except SQLAlchemyError as e:
#         logger.error(f"Error de base de datos al actualizar hogar: {str(e)}")
#         await db.rollback()
#         raise
#     except Exception as e:
#         logger.error(f"Error inesperado al actualizar hogar: {str(e)}")
#         await db.rollback()
#         raise

# async def eliminar_hogar_logico(db: AsyncSession, hogar_id: int):
#     try:
#         logger.info(f"Eliminando (lógico) hogar con ID: {hogar_id}")
#         hogar = await db.get(Hogar, hogar_id)
#         if hogar and hogar.estado:
#             hogar.estado = False
#             await db.commit()
#             logger.info(f"Hogar eliminado lógicamente: {hogar_id}")
#             return True
#         logger.warning(f"No se pudo eliminar hogar con ID: {hogar_id}")
#         return False
#     except SQLAlchemyError as e:
#         logger.error(f"Error de base de datos al eliminar hogar: {str(e)}")
#         await db.rollback()
#         raise
#     except Exception as e:
#         logger.error(f"Error inesperado al eliminar hogar: {str(e)}")
#         await db.rollback()
#         raise

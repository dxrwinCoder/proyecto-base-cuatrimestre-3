from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.miembro import Miembro
from sqlalchemy.orm import selectinload
from utils.security import verificar_contrasena, obtener_hash_contrasena, crear_token_acceso
from datetime import timedelta
from config.config import settings
from utils.logger import setup_logger
from sqlalchemy.exc import SQLAlchemyError

logger = setup_logger("auth_service")

async def autenticar_miembro(db: AsyncSession, correo: str, contrasena: str):
    try:
        logger.info(f"Intentando autenticar al miembro con correo: {correo}")
        result = await db.execute(
            select(Miembro).options(selectinload(Miembro.rol)).where(Miembro.correo_electronico == correo)
        )
        miembro = result.scalar_one_or_none()
        
        if not miembro:
            logger.warning(f"No se encontró ningún miembro con el correo: {correo}")
            return None
            
        if not verificar_contrasena(contrasena, miembro.contrasena_hash):
            logger.warning(f"Contraseña incorrecta para el correo: {correo}")
            return None
            
        logger.info(f"Autenticación exitosa para el miembro: {miembro.nombre_completo}")
        return miembro
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos durante la autenticación: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado durante la autenticación: {str(e)}")
        raise

async def crear_miembro(db: AsyncSession, datos_registro):
    try:
        logger.info(f"Intentando crear nuevo miembro con correo: {datos_registro.correo_electronico}")
        
        # Verificar que el correo no exista
        existe = await db.execute(
            Miembro.__table__.select().where(Miembro.correo_electronico == datos_registro.correo_electronico)
        )
        if existe.scalar_one_or_none():
            logger.warning(f"Intento de registro con correo ya existente: {datos_registro.correo_electronico}")
            raise ValueError("El correo electrónico ya se encuentra registrado en el sistema")

        nuevo = Miembro(
            nombre_completo=datos_registro.nombre_completo,
            correo_electronico=datos_registro.correo_electronico,
            contrasena_hash=obtener_hash_contrasena(datos_registro.contrasena),
            id_rol=datos_registro.id_rol,
            id_hogar=datos_registro.id_hogar
        )
        
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo, with_for_update=True)
        
        logger.info(f"Miembro creado exitosamente: {nuevo.nombre_completo}")
        return nuevo
        
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al crear miembro: {str(e)}")
        await db.rollback()
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al crear miembro: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear miembro: {str(e)}")
        await db.rollback()
        raise

def crear_token_para_miembro(miembro: Miembro):
    try:
        logger.info(f"Generando token de acceso para miembro: {miembro.nombre_completo}")
        data = {
            "sub": str(miembro.id),
            "rol": miembro.rol.nombre,
            "id_hogar": miembro.id_hogar
        }
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = crear_token_acceso(data, expires_delta=access_token_expires)
        logger.info("Token de acceso generado exitosamente")
        return token
    except Exception as e:
        logger.error(f"Error al crear token para miembro {miembro.nombre_completo}: {str(e)}")
        raise
#from h11 import Data
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from config.config import settings
from utils.logger import setup_logger

logger = setup_logger("security")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def obtener_hash_contrasena(contrasena: str) -> str:
    try:
        logger.info("Generando hash de contraseña")
        if len(contrasena) > 72:
            contrasena = contrasena[:72]
            logger.warning("Contraseña truncada a 72 caracteres debido a limitación de bcrypt")
        hash_result = pwd_context.hash(contrasena)
        logger.info("Hash de contraseña generado exitosamente")
        return hash_result
    except Exception as e:
        logger.error(f"Error al generar hash de contraseña: {str(e)}")
        raise

def verificar_contrasena(contrasena: str, hash_contrasena: str) -> bool:
    try:
        logger.info("Verificando contraseña")
        resultado = pwd_context.verify(contrasena, hash_contrasena)
        if resultado:
            logger.info("Contraseña verificada correctamente")
        else:
            logger.warning("Verificación de contraseña fallida")
        return resultado
    except Exception as e:
        logger.error(f"Error al verificar contraseña: {str(e)}")
        raise

def crear_token_acceso(data: dict, expires_delta: timedelta = None) -> str:
    try:
        logger.info("Generando token de acceso")
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
        to_encode.update({"exp": expire})
        token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.info("Token de acceso generado exitosamente")
        return token
    except Exception as e:
        logger.error(f"Error al crear token de acceso: {str(e)}")
        raise

def decode_jwt(token: str):
    try:
        logger.info("Decodificando token JWT")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info("Token JWT decodificado exitosamente")
        return payload
    except JWTError as e:
        logger.warning(f"Error al decodificar token JWT: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al decodificar token JWT: {str(e)}")
        raise
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from utils.auth import obtener_miembro_actual
from services.permiso_service import verificar_permiso
from utils.logger import setup_logger

# Configurar logger específico para el módulo de permisos
logger = setup_logger("permissions")


def require_permission(modulo_nombre: str, accion: str):
    """
    Decorador que verifica si el usuario actual tiene permisos para realizar una acción específica.

    Este decorador se utiliza para proteger endpoints que requieren permisos específicos.
    Verifica automáticamente los permisos del usuario autenticado antes de permitir
    el acceso a la funcionalidad protegida.

    Args:
        modulo_nombre (str): Nombre del módulo al que pertenece la acción
        accion (str): Acción específica a verificar (crear, leer, actualizar, eliminar)

    Returns:
        function: Decorador que envuelve la función original

    Raises:
        HTTPException: Si el usuario no tiene permisos suficientes
    """

    async def _wrapper(
        current_user=Depends(obtener_miembro_actual), db: AsyncSession = Depends(get_db)
    ):
        """
        Función interna que realiza la verificación de permisos.

        Args:
            current_user: Usuario autenticado obtenido del token
            db (AsyncSession): Sesión de base de datos para realizar consultas

        Returns:
            Miembro: Usuario autenticado si tiene permisos

        Raises:
            HTTPException: Si no se tienen los permisos necesarios
        """
        try:
            # Superuser: rol 1 no requiere verificación de permisos específicos
            if getattr(current_user, "id_rol", None) == 1:
                logger.info(
                    f"Acceso autorizado automático: Usuario {current_user.id} es rol 1 (admin)."
                )
                return current_user
            # Permitir que un miembro consulte su propio perfil sin permisos explícitos
            if modulo_nombre == "Miembros" and accion == "leer":
                return current_user

            # Registrar el intento de verificación de permisos
            logger.info(
                f"Verificando permisos para usuario {current_user.id} "
                f"en módulo '{modulo_nombre}' para acción '{accion}'"
            )

            # Verificar si el usuario actual tiene el permiso requerido
            # para realizar la acción especificada en el módulo dado
            if not await verificar_permiso(db, current_user.id, modulo_nombre, accion):
                # Registrar el acceso denegado
                logger.warning(
                    f"Acceso denegado: Usuario {current_user.id} "
                    f"no tiene permisos para '{accion}' en módulo '{modulo_nombre}'"
                )

                # Si no tiene permisos, lanzar excepción HTTP 403 (Forbidden)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para esta acción",
                )

            # Registrar el acceso exitoso
            logger.info(
                f"Acceso autorizado: Usuario {current_user.id} "
                f"tiene permisos para '{accion}' en módulo '{modulo_nombre}'"
            )

            # Si tiene permisos, devolver el usuario autenticado
            return current_user

        except HTTPException as e:
            # Re-lanzar excepciones HTTP para mantener el código de estado
            logger.error(
                f"Error HTTP en verificación de permisos: {e.status_code} - {e.detail}"
            )
            raise
        except Exception as e:
            # Registrar errores inesperados
            logger.error(
                f"Error inesperado al verificar permisos para usuario {current_user.id}: {str(e)}"
            )

            # Manejar cualquier otro error inesperado
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al verificar permisos",
            )

    return _wrapper

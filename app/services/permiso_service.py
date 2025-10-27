from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.permiso import Permiso
from models.miembro import Miembro
from models.rol import Rol
from models.modulo import Modulo


async def asignar_permiso(db: AsyncSession, data: dict):
    """
    Asigna un nuevo permiso en la base de datos.

    Args:
        db (AsyncSession): Sesión de base de datos asíncrona
        data (dict): Diccionario con los datos del permiso a crear

    Returns:
        Permiso: El permiso recién creado

    Raises:
        Exception: Si hay un error durante la creación del permiso
    """
    try:
        # Crear una instancia de Permiso con los datos proporcionados
        permiso = Permiso(**data)

        # Añadir el nuevo permiso a la sesión de base de datos
        db.add(permiso)

        # Confirmar la transacción
        await db.commit()

        # Actualizar el objeto con los datos de la base de datos
        await db.refresh(permiso)

        return permiso
    except Exception as e:
        # Revertir la transacción en caso de error
        await db.rollback()
        # Registrar el error o relanzar una excepción más específica
        raise ValueError(f"Error al asignar permiso: {str(e)}")


async def obtener_permisos_por_rol(db: AsyncSession, rol_id: int):
    """
    Obtiene todos los permisos activos para un rol específico.

    Args:
        db (AsyncSession): Sesión de base de datos asíncrona
        rol_id (int): Identificador del rol

    Returns:
        list: Lista de permisos activos para el rol
    """
    try:
        # Consulta para obtener permisos activos de un rol específico
        stmt = select(Permiso).where(Permiso.id_rol == rol_id, Permiso.estado == True)

        # Ejecutar la consulta
        result = await db.execute(stmt)

        # Devolver todos los permisos encontrados
        return result.scalars().all()
    except Exception as e:
        # Manejar cualquier error durante la consulta
        raise ValueError(f"Error al obtener permisos por rol: {str(e)}")


async def actualizar_permiso(db: AsyncSession, permiso_id: int, updates: dict):
    """
    Actualiza un permiso existente en la base de datos.

    Args:
        db (AsyncSession): Sesión de base de datos asíncrona
        permiso_id (int): Identificador del permiso a actualizar
        updates (dict): Diccionario con los campos a actualizar

    Returns:
        Permiso|None: El permiso actualizado o None si no se encuentra
    """
    try:
        # Obtener el permiso por su ID
        permiso = await db.get(Permiso, permiso_id)

        # Verificar si el permiso existe y está activo
        if permiso and permiso.estado:
            # Actualizar los atributos del permiso
            for k, v in updates.items():
                setattr(permiso, k, v)

            # Confirmar los cambios
            await db.commit()
            return permiso

        # Retornar None si el permiso no existe o no está activo
        return None
    except Exception as e:
        # Revertir la transacción en caso de error
        await db.rollback()
        raise ValueError(f"Error al actualizar permiso: {str(e)}")


async def verificar_permiso(
    db: AsyncSession, id_miembro: int, modulo_nombre: str, accion: str
):
    """
    Verifica si un miembro tiene permiso para realizar una acción específica en un módulo.

    Args:
        db (AsyncSession): Sesión de base de datos asíncrona
        id_miembro (int): Identificador del miembro
        modulo_nombre (str): Nombre del módulo
        accion (str): Acción a verificar (crear, leer, actualizar, eliminar)

    Returns:
        bool: True si tiene permiso, False en caso contrario
    """
    try:
        # Obtener el miembro por su ID
        miembro = await db.get(Miembro, id_miembro)

        # Verificar si el miembro existe y está activo
        if not miembro or not miembro.estado:
            return False

        # Construir consulta para verificar permisos
        stmt = (
            select(Permiso)
            .join(Rol, Permiso.id_rol == Rol.id)
            .join(Modulo, Permiso.id_modulo == Modulo.id)
            .where(
                Rol.id == miembro.id_rol,
                Modulo.nombre == modulo_nombre,
                Permiso.estado == True,
            )
        )

        # Ejecutar la consulta
        result = await db.execute(stmt)
        permiso = result.scalar_one_or_none()

        # Si no se encuentra un permiso, denegar el acceso
        if not permiso:
            return False

        # Verificar el permiso específico para la acción
        # Usa getattr para verificar dinámicamente el atributo de permiso
        # (puede_crear, puede_leer, puede_actualizar, puede_eliminar)
        return getattr(permiso, f"puede_{accion}", False)

    except Exception as e:
        # Manejar cualquier error durante la verificación
        # En producción, podrías querer registrar este error
        return False

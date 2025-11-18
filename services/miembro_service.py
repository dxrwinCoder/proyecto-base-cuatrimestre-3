from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from models.miembro import Miembro
from models.rol import Rol
from models.tarea import Tarea
from services.auth_service import _asignar_permisos_totales_a_rol
from utils.security import obtener_hash_contrasena
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import setup_logger

logger = setup_logger("miembro_service")


async def crear_miembro(db: AsyncSession, data: dict):
    """
    Servicio "calibrado" para que un Admin cree otros miembros.
    - Usa db.flush() (no commit).
    - Asigna permisos si el nuevo miembro es también Admin (id_rol=1).
    """
    try:
        logger.info(f"Creando nuevo miembro: {data['nombre_completo']}")

        # 1. Verificar si ya existe el correo
        existe = await db.execute(
            select(Miembro).where(
                Miembro.correo_electronico == data["correo_electronico"]
            )
        )
        if existe.scalar_one_or_none():
            logger.warning(
                f"Intento de crear miembro con correo existente: {data['correo_electronico']}"
            )
            raise ValueError("El correo electrónico ya está registrado")

        # 2. (Validación de 'miembro_routes') La ruta ya verifica que el hogar exista

        miembro = Miembro(
            nombre_completo=data["nombre_completo"],
            correo_electronico=data["correo_electronico"],
            contrasena_hash=obtener_hash_contrasena(data["contrasena"]),
            id_rol=data["id_rol"],
            id_hogar=data["id_hogar"],
        )
        db.add(miembro)
        await db.flush()  # <-- ¡CAMBIO A FLUSH!

        # 3. ¡LÓGICA DE PERMISOS AÑADIDA!
        # Si el Admin está creando a OTRO Admin
        if miembro.id_rol == 1:
            # Reutilizamos la lógica del auth_service
            await _asignar_permisos_totales_a_rol(db, miembro.id_rol)

        # 4. Recargar con rol usando eager loading
        result = await db.execute(
            select(Miembro)
            .options(joinedload(Miembro.rol))
            .where(Miembro.id == miembro.id)
        )
        miembro_con_rol = result.scalar_one()

        logger.info(f"Miembro creado (sin commit) exitosamente: {miembro_con_rol.id}")
        return miembro_con_rol

    except (ValueError, SQLAlchemyError, Exception) as e:
        logger.error(f"Error al crear miembro (rollback pendiente): {str(e)}")
        raise  # Relanzar para que la ruta maneje el rollback


async def obtener_miembro(db: AsyncSession, miembro_id: int):
    try:
        logger.info(f"Buscando miembro con ID: {miembro_id}")
        query = (
            select(Miembro)
            .options(joinedload(Miembro.rol))
            .where(Miembro.id == miembro_id)
        )
        result = await db.execute(query)
        miembro = result.scalar_one_or_none()

        if miembro:
            logger.info(f"Miembro encontrado: {miembro.nombre_completo}")
        else:
            logger.warning(f"Miembro no encontrado con ID: {miembro_id}")

        return miembro
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al obtener miembro: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener miembro: {str(e)}")
        raise


async def listar_miembros_activos_por_hogar(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Listando miembros activos del hogar: {hogar_id}")
        query = (
            select(Miembro)
            .options(joinedload(Miembro.rol))
            .where(and_(Miembro.id_hogar == hogar_id, Miembro.estado == True))
        )
        result = await db.execute(query)
        miembros = result.scalars().all()
        logger.info(f"Se encontraron {len(miembros)} miembros activos")
        return miembros
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al listar miembros: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al listar miembros: {str(e)}")
        raise


async def actualizar_miembro(db: AsyncSession, miembro_id: int, data: dict):
    try:
        logger.info(f"Actualizando miembro: {miembro_id}")
        # Usar select con joinedload para cargar el rol
        query = (
            select(Miembro)
            .options(joinedload(Miembro.rol))
            .where(Miembro.id == miembro_id)
        )
        result = await db.execute(query)
        miembro = result.scalar_one_or_none()

        if not miembro:
            logger.warning(f"Miembro no encontrado para actualizar: {miembro_id}")
            return None

        # Verificar si el correo nuevo ya existe
        if (
            "correo_electronico" in data
            and data["correo_electronico"] != miembro.correo_electronico
        ):
            existe = await db.execute(
                select(Miembro).where(
                    Miembro.correo_electronico == data["correo_electronico"]
                )
            )
            if existe.scalar_one_or_none():
                logger.warning(
                    f"Correo electrónico ya existe: {data['correo_electronico']}"
                )
                raise ValueError("El correo electrónico ya está registrado")

        for key, value in data.items():
            if value is not None:
                setattr(miembro, key, value)

        await db.commit()
        # await db.refresh(miembro, ["rol"])  # Refrescar incluyendo el rol
        logger.info(f"Miembro actualizado exitosamente: {miembro_id}")
        # ¡Use la función que ya carga el objeto con el 'joinedload' (rol)!
        return await obtener_miembro(db, miembro_id)
    except ValueError as e:
        logger.error(f"Error de validación al actualizar miembro: {str(e)}")
        raise
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al actualizar miembro: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al actualizar miembro: {str(e)}")
        await db.rollback()
        raise


async def desactivar_miembro(db: AsyncSession, miembro_id: int):
    try:
        logger.info(f"Desactivando miembro: {miembro_id}")
        miembro = await db.get(Miembro, miembro_id)

        if not miembro:
            logger.warning(f"Miembro no encontrado para desactivar: {miembro_id}")
            return False

        if not miembro.estado:
            logger.warning(f"Miembro ya está desactivado: {miembro_id}")
            return False

        miembro.estado = False
        await db.commit()
        logger.info(f"Miembro desactivado exitosamente: {miembro_id}")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al desactivar miembro: {str(e)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al desactivar miembro: {str(e)}")
        await db.rollback()
        raise


async def obtener_todos_los_miembros(db: AsyncSession):
    try:
        logger.info("Obteniendo todos los miembros")
        query = select(Miembro).options(joinedload(Miembro.rol))
        result = await db.execute(query)
        miembros = result.scalars().all()
        logger.info(f"Se encontraron {len(miembros)} miembros")
        return miembros
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al obtener todos los miembros: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener todos los miembros: {str(e)}")
        raise


async def contar_miembros_por_hogar(db: AsyncSession, hogar_id: int):
    try:
        logger.info(f"Contando miembros activos del hogar: {hogar_id}")
        query = select(func.count(Miembro.id)).where(
            and_(Miembro.id_hogar == hogar_id, Miembro.estado == True)
        )
        result = await db.execute(query)
        cantidad = result.scalar_one()
        logger.info(f"Se encontraron {cantidad} miembros activos")
        return cantidad
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al contar miembros: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al contar miembros: {str(e)}")
        raise


async def obtener_miembros_por_rol(db: AsyncSession, rol_id: int):
    try:
        logger.info(f"Obteniendo miembros con rol: {rol_id}")
        query = (
            select(Miembro)
            .options(joinedload(Miembro.rol))
            .where(and_(Miembro.id_rol == rol_id, Miembro.estado == True))
        )
        result = await db.execute(query)
        miembros = result.scalars().all()
        logger.info(f"Se encontraron {len(miembros)} miembros con el rol {rol_id}")
        return miembros
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al obtener miembros por rol: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener miembros por rol: {str(e)}")
        raise


async def obtener_miembro_por_nombre(
    db: AsyncSession, nombre: str, hogar_id: int
) -> Miembro | None:
    """
    Busca un miembro activo por su nombre completo (o parcial)
    dentro de un hogar específico.
    Carga la relación 'rol' para uso futuro.
    """
    try:
        logger.info(f"Buscando miembro por nombre '{nombre}' en hogar {hogar_id}")

        stmt = (
            select(Miembro)
            .where(
                Miembro.nombre_completo.ilike(
                    f"%{nombre}%"
                ),  # ilike = case-insensitive
                Miembro.id_hogar == hogar_id,
                Miembro.estado == True,
            )
            .options(joinedload(Miembro.rol))
        )  # Cargar el rol

        result = await db.execute(stmt)
        miembro = result.scalars().first()

        if miembro:
            logger.info(f"Miembro encontrado por nombre: {miembro.nombre_completo}")
        else:
            logger.warning(f"Miembro no encontrado por nombre: {nombre}")

        return miembro

    except Exception as e:
        logger.error(f"Error al buscar miembro por nombre: {str(e)}")
        raise


async def listar_miembros_activos_por_hogar(
    db: AsyncSession, hogar_id: int
) -> list[Miembro]:
    """
    Lista todos los miembros activos de un hogar, cargando sus roles.
    """
    try:
        logger.info(f"Listando miembros activos del hogar: {hogar_id}")
        stmt = (
            select(Miembro)
            .where(Miembro.id_hogar == hogar_id, Miembro.estado == True)
            .options(joinedload(Miembro.rol))
        )  # Cargar roles

        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error al listar miembros: {str(e)}")
        raise


async def listar_tareas_por_estado_y_hogar(
    db: AsyncSession, estado: str, hogar_id: int
) -> list[Tarea]:
    """
    Lista tareas de un hogar filtradas por estado_actual.
    Carga el miembro asignado para evitar N+1.
    """
    try:
        logger.info(f"Listando tareas con estado '{estado}' en hogar {hogar_id}")
        stmt = (
            select(Tarea)
            .where(
                Tarea.id_hogar == hogar_id,
                Tarea.estado_actual == estado,
                Tarea.estado == True,  # No borradas lógicamente
            )
            .options(joinedload(Tarea.miembro_asignado))
        )  # Cargar el miembro asignado

        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error al listar tareas por estado: {str(e)}")
        raise

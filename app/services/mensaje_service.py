from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from models.mensaje import Mensaje
from models.tarea import Tarea
from uuid import uuid4
from utils.logger import setup_logger

logger = setup_logger("mensaje_service")


async def crear_sesion_mensaje_para_tarea(db: AsyncSession, tarea_id: int):
    try:
        logger.info(f"Creando sesión de mensaje para tarea {tarea_id}")
        tarea = await db.get(Tarea, tarea_id)
        if not tarea or not tarea.estado:
            logger.warning(
                f"No se puede crear sesión: tarea {tarea_id} no existe o está inactiva"
            )
            return None

        sesion_id = str(uuid4())
        tarea.id_sesion_mensaje = sesion_id
        await db.commit()
        logger.info(f"Sesión creada con ID: {sesion_id} para tarea {tarea_id}")
        return sesion_id
    except Exception as e:
        logger.error(f"Error al crear sesión para tarea {tarea_id}: {str(e)}")
        await db.rollback()
        raise


async def enviar_mensaje_en_sesion(
    db: AsyncSession, sesion_id: str, remitente_id: int, contenido: str
):
    try:
        logger.info(
            f"Enviando mensaje en sesión {sesion_id} por remitente {remitente_id}"
        )
        stmt = select(Tarea).where(
            Tarea.id_sesion_mensaje == sesion_id, Tarea.estado == True
        )
        result = await db.execute(stmt)
        tarea_obj = result.scalar_one_or_none()

        if not tarea_obj:
            logger.error(f"Sesión {sesion_id} no vinculada a ninguna tarea activa")
            raise ValueError("Sesión inválida o tarea inactiva")

        mensaje = Mensaje(
            id_hogar=tarea_obj.id_hogar, id_remitente=remitente_id, contenido=contenido
        )
        db.add(mensaje)
        await db.commit()
        await db.refresh(mensaje)
        logger.info(f"Mensaje enviado en sesión {sesion_id}, ID mensaje: {mensaje.id}")
        return mensaje
    except Exception as e:
        logger.error(f"Error al enviar mensaje en sesión {sesion_id}: {str(e)}")
        await db.rollback()
        raise


async def obtener_mensajes_por_hogar(db: AsyncSession, hogar_id: int):
    """
    Obtiene TODOS los mensajes de un hogar, cargando el remitente (Miembro)
    para evitar N+1 queries.
    """
    try:
        logger.info(f"Obteniendo mensajes del hogar {hogar_id}")

        stmt_mensajes = (
            select(Mensaje)
            .where(Mensaje.id_hogar == hogar_id, Mensaje.estado == True)
            .options(joinedload(Mensaje.remitente))  # <-- ¡EL PARCHE N+1!
            .order_by(Mensaje.fecha_envio.asc())
        )

        result_mensajes = await db.execute(stmt_mensajes)
        mensajes = result_mensajes.scalars().all()

        logger.info(f"Se recuperaron {len(mensajes)} mensajes para el hogar {hogar_id}")
        return mensajes
    except Exception as e:
        logger.error(f"Error al obtener mensajes del hogar {hogar_id}: {str(e)}")
        raise

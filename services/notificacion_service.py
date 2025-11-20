# services/notificacion_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.notificacion import Notificacion
from schemas.notificacion import NotificacionCreate
from utils.logger import setup_logger

logger = setup_logger("notificacion_service")


async def crear_notificacion(db: AsyncSession, notificacion_data: NotificacionCreate):
    """
    Servicio interno para crear una notificación.
    NO hace commit; la ruta/servicio llamante debe confirmar la transacción.
    """
    try:
        notificacion = Notificacion(**notificacion_data.dict())
        db.add(notificacion)
        await db.flush()
        await db.refresh(notificacion)
        logger.info(
            f"Notificación creada (sin commit) para miembro {notificacion.id_miembro_destino}"
        )
        return notificacion
    except Exception as e:
        logger.error(f"Error al crear notificación: {str(e)}")
        # No relanzamos; la acción principal no debe fallar por la notificación.
        return None


async def listar_notificaciones_por_miembro(db: AsyncSession, miembro_id: int):
    """
    Lista notificaciones activas para un miembro.
    """
    stmt = (
        select(Notificacion)
        .where(Notificacion.id_miembro_destino == miembro_id, Notificacion.estado == 1)
        .order_by(Notificacion.fecha_creacion.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

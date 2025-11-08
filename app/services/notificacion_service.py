# services/notificacion_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from models.notificacion import Notificacion
from schemas.notificacion import NotificacionCreate  # ¡Asumo que tiene este schema!
from utils.logger import setup_logger

logger = setup_logger("notificacion_service")


async def crear_notificacion(db: AsyncSession, notificacion_data: NotificacionCreate):
    """
    Servicio interno para crear una notificación.
    ¡OJO! Esta función NO hace commit. Espera que la ruta/servicio que la llama lo haga.
    """
    try:
        notificacion = Notificacion(**notificacion_data.model_dump())
        db.add(notificacion)
        await db.flush()
        await db.refresh(notificacion)
        logger.info(
            f"Notificación creada (sin commit) para miembro {notificacion.id_miembro_destino}"
        )
        return notificacion
    except Exception as e:
        logger.error(f"Error al crear notificación: {str(e)}")
        # No relanzamos el error, porque si falla la notificación,
        # la tarea (la acción principal) NO debe fallar.
        return None

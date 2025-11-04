from sqlalchemy.ext.asyncio import AsyncSession
from models.comentario_tarea import ComentarioTarea
from models.notificacion import Notificacion
from utils.logger import setup_logger

logger = setup_logger("comentario_service")


async def agregar_comentario_a_tarea(db: AsyncSession, data: dict):
    try:
        logger.info(f"Agregando comentario a tarea {data['id_tarea']}")
        comentario = ComentarioTarea(**data)
        db.add(comentario)
        await db.commit()
        await db.refresh(comentario)

        # Notificar al asignado de la tarea
        notif = Notificacion(
            id_miembro_destino=data[
                "id_tarea"
            ],  # ajustar lógica si el creador es diferente
            id_miembro_origen=data["id_miembro"],
            id_tarea=data["id_tarea"],
            tipo="nuevo_comentario",
            mensaje="Se agregó un comentario a la tarea",
        )
        db.add(notif)
        await db.commit()
        return comentario
    except Exception as e:
        logger.error(f"Error al agregar comentario: {str(e)}")
        await db.rollback()
        raise

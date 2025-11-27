from fastapi import APIRouter, HTTPException

from .config import WhatsAppConfig
from .schemas import NotificationPayload
from .service import WhatsAppNotificationService
from utils.logger import setup_logger

router = APIRouter(prefix="/notificaciones/whatsapp", tags=["WhatsApp Cloud API"])
logger = setup_logger("whatsapp_router")


def get_service() -> WhatsAppNotificationService:
    """
    Factory simple para crear el servicio con configuracion desde env.
    """
    config = WhatsAppConfig.from_env()
    return WhatsAppNotificationService(config)


@router.post("/enviar")
async def enviar_notificacion(payload: NotificationPayload):
    """
    Endpoint directo para disparar una notificacion de WhatsApp con la plantilla aprobada.
    Usa la IA interna para rellenar las variables si no se mandan override_variables.
    """
    logger.info(
        "POST /notificaciones/whatsapp/enviar evento=%s destinatario=%s",
        payload.evento.value,
        payload.destinatario.telefono,
    )
    try:
        servicio = get_service()
        logger.debug(
            "Instanciado servicio WhatsApp con plantilla=%s lang=%s",
            servicio.config.template_name,
            servicio.config.template_language,
        )
        respuesta = await servicio.enviar(payload)
        logger.info(
            "Envio completado evento=%s destinatario=%s",
            payload.evento.value,
            payload.destinatario.telefono,
        )
        return {
            "status": "queued",
            "response": respuesta,
            "evento": payload.evento,
        }
    except Exception as exc:
        logger.error("No se pudo enviar notificacion: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

"""
Script manual para probar el envio de una plantilla por WhatsApp Cloud API.
Requiere variables de entorno:
- WHATSAPP_PHONE_NUMBER_ID
- WHATSAPP_ACCESS_TOKEN
- WHATSAPP_TEMPLATE_NAME
- WHATSAPP_TEMPLATE_LANG (opcional, por defecto es)

Uso:
  python scripts/test_whatsapp_template.py --to +5215555555555 --name John --detalle "Tarea de prueba" --fecha 2025-12-31 --contacto support@example.com
"""

import argparse
import asyncio
import os
from datetime import datetime

from notificaciones_cloud_api.config import WhatsAppConfig
from notificaciones_cloud_api.schemas import (
    NotificationPayload,
    NotificationEvent,
    Destinatario,
    ContextoTarea,
)
from notificaciones_cloud_api.service import WhatsAppNotificationService
from utils.logger import setup_logger

logger = setup_logger("test_whatsapp_template")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probar envio de plantilla WhatsApp.")
    parser.add_argument(
        "--to",
        required=True,
        help="Numero destino en formato E.164, ej. +5215555555555",
    )
    parser.add_argument("--name", default="Usuario", help="Nombre para {{1}}")
    parser.add_argument("--detalle", default="Actividad de prueba", help="Texto para {{2}}")
    parser.add_argument("--fecha", default="", help="Fecha o texto para {{3}}")
    parser.add_argument("--contacto", default="soporte@example.com", help="Texto para {{4}}")
    parser.add_argument(
        "--evento",
        default="tarea_por_vencer",
        choices=[e.value for e in NotificationEvent],
        help="Tipo de evento a enviar",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    # Validar env necesarios
    missing = [
        env for env in ["WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN"] if not os.getenv(env)
    ]
    if missing:
        raise SystemExit(f"Faltan variables de entorno: {', '.join(missing)}")

    config = WhatsAppConfig.from_env()
    service = WhatsAppNotificationService(config)

    payload = NotificationPayload(
        evento=NotificationEvent(args.evento),
        destinatario=Destinatario(
            nombre=args.name,
            telefono=args.to,
            rol_id=2,
            contacto=args.contacto,
        ),
        tarea=ContextoTarea(
            titulo=args.detalle,
            fecha_limite=None if not args.fecha else datetime.fromisoformat(args.fecha).date()
        ),
        override_variables=[args.name, args.detalle, args.fecha, args.contacto],
    )

    logger.info("Enviando plantilla %s a %s", config.template_name, args.to)
    response = await service.enviar(payload)
    logger.info("Respuesta: %s", response)
    print("Listo. Verifica el mensaje en el telefono destino.")


if __name__ == "__main__":
    asyncio.run(main())

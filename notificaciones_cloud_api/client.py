from typing import List, Optional

import httpx

from utils.logger import setup_logger
from .config import WhatsAppConfig

logger = setup_logger("whatsapp_client")


class WhatsAppCloudClient:
    """
    Cliente minimo para enviar plantillas por WhatsApp Cloud API.
    """

    def __init__(self, config: WhatsAppConfig):
        self.config = config

    async def send_template_message(
        self,
        to: str,
        body_vars: List[str],
        template_name: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        template = template_name or self.config.template_name
        lang = language or self.config.template_language

        url = f"https://graph.facebook.com/{self.config.api_version}/{self.config.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": lang},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": v} for v in body_vars],
                    }
                ],
            },
        }

        logger.info(
            "Llamando a WhatsApp API template=%s lang=%s destino=%s vars=%s",
            template,
            lang,
            to,
            len(body_vars),
        )
        logger.debug("Payload body vars: %s", body_vars)
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            logger.error(
                "Error de WhatsApp API (%s): %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"WhatsApp API devolvio {response.status_code}: {response.text}"
            )

        data = response.json()
        message_id = None
        try:
            message_id = data.get("messages", [{}])[0].get("id")
        except Exception:
            pass
        logger.info("Mensaje encolado en WhatsApp message_id=%s", message_id)
        return data

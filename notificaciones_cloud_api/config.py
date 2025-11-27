import os
from dataclasses import dataclass
from typing import List


@dataclass
class WhatsAppConfig:
    """
    Configuracion minima para consumir WhatsApp Cloud API.
    Lee las variables de entorno esperadas en la plataforma de Meta.
    """

    phone_number_id: str
    access_token: str
    template_name: str
    template_language: str = "es"
    api_version: str = "v19.0"
    timeout_seconds: float = 10.0
    body_variables_expected: int = 4  # Segun la plantilla del screenshot.
    default_contact: str = ""

    @classmethod
    def from_env(cls) -> "WhatsAppConfig":
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
        access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
        template_name = os.getenv("WHATSAPP_TEMPLATE_NAME").strip()
        template_language = os.getenv("WHATSAPP_TEMPLATE_LANG", "es").strip()
        api_version = os.getenv("WHATSAPP_API_VERSION", "v19.0").strip()
        default_contact = os.getenv("WHATSAPP_DEFAULT_CONTACT", "").strip()

        missing: List[str] = []
        if not phone_number_id:
            missing.append("WHATSAPP_PHONE_NUMBER_ID")
        if not access_token:
            missing.append("WHATSAPP_ACCESS_TOKEN")
        if missing:
            raise RuntimeError(
                f"Faltan variables de entorno para WhatsApp: {', '.join(missing)}"
            )

        return cls(
            phone_number_id=phone_number_id,
            access_token=access_token,
            template_name=template_name,
            template_language=template_language or "es",
            api_version=api_version or "v19.0",
            default_contact=default_contact,
        )

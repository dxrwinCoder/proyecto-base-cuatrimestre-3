from datetime import date
from typing import List

from utils.logger import setup_logger

from .ai_renderer import render_body_vars_with_ai
from .client import WhatsAppCloudClient
from .config import WhatsAppConfig
from .schemas import NotificationPayload, NotificationEvent

logger = setup_logger("whatsapp_service")


class WhatsAppNotificationService:
    """
    Orquesta el render de variables y el envio por WhatsApp Cloud API.
    """

    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self.client = WhatsAppCloudClient(config)

    async def enviar(self, payload: NotificationPayload) -> dict:
        """
        Envia una notificacion usando la plantilla configurada.
        """
        logger.info(
            "Preparando envio evento=%s telefono=%s",
            payload.evento.value,
            payload.destinatario.telefono,
        )
        template_name = payload.template_name or self.config.template_name
        template_language = payload.template_language or self.config.template_language
        expected_vars = payload.body_variables_expected or self.config.body_variables_expected

        variables = payload.override_variables or await self._build_variables(
            payload, expected_vars, template_name
        )
        logger.debug("Variables de plantilla listas: %s", variables)
        return await self.client.send_template_message(
            to=payload.destinatario.telefono,
            body_vars=variables,
            template_name=template_name,
            language=template_language,
        )

    async def _build_variables(
        self, payload: NotificationPayload, expected_count: int, template_name: str
    ) -> List[str]:
        """
        Arma el array en el orden {{1}}, {{2}}, {{3}}, {{4}} basado en el screenshot.
        Si falla la IA, se usa un fallback determinista.
        """
        dest = payload.destinatario
        tarea = payload.tarea
        comentario = payload.comentario

        contacto = dest.contacto or self.config.default_contact or "soporte"
        nombre = dest.nombre or "Miembro"
        fecha_ref: str = ""
        descripcion_corta = ""
        hora_evento = payload.metadata.get("hora") or payload.metadata.get("hora_evento")
        fecha_evento_extra = payload.metadata.get("fecha_evento")

        if tarea:
            descripcion_corta = tarea.titulo or tarea.descripcion or "Tu tarea"
            if tarea.fecha_limite:
                fecha_ref = tarea.fecha_limite.isoformat()
        if payload.evento == NotificationEvent.ASIGNADO_EVENTO and tarea:
            descripcion_corta = tarea.evento_titulo or descripcion_corta

        if payload.evento == NotificationEvent.TAREA_COMPLETADA:
            descripcion_corta = f"Tarea completada: {descripcion_corta or 'tarea'}"
        elif payload.evento == NotificationEvent.TAREA_VENCIDA:
            descripcion_corta = f"Tarea vencida: {descripcion_corta or 'tarea'}"
        elif payload.evento == NotificationEvent.CAMBIO_ESTADO_TAREA and tarea:
            estado = tarea.estado or "actualizada"
            descripcion_corta = (
                f"Tarea '{tarea.titulo or 'tarea'}' cambiada a '{estado}'"
            )

        if payload.evento == NotificationEvent.COMENTARIO_TAREA and comentario:
            descripcion_corta = (
                f"Nuevo comentario: {comentario.contenido or 'Comentario en tu tarea'}"
            )
            if comentario.tarea_titulo:
                descripcion_corta += f" en '{comentario.tarea_titulo}'"

        # Determinar orden de variables segun plantilla
        if payload.variable_order:
            variable_order = payload.variable_order
        else:
            variable_order = (
                ["fecha", "hora"]
                if expected_count == 2
                else ["nombre", "detalle", "fecha", "contacto"]
            )

        # Mapear valores por token
        value_map = {
            "nombre": nombre,
            "detalle": descripcion_corta or "Actividad asignada",
            "fecha": fecha_ref or fecha_evento_extra or "",
            "contacto": contacto,
            "evento_fecha": fecha_ref or fecha_evento_extra or "",
            "evento_hora": hora_evento or "",
            "hora": hora_evento or "",
        }

        # Construir fallback segun orden
        fallback: List[str] = []
        for token in variable_order:
            fallback.append(value_map.get(token, "Sin dato"))

        # Ajustar longitud por si el orden difiere del expected_count
        if len(fallback) < expected_count:
            fallback.extend(["Sin dato"] * (expected_count - len(fallback)))
        elif len(fallback) > expected_count:
            fallback = fallback[:expected_count]

        contexto = {
            "evento": payload.evento.value,
            "destinatario": dest.dict(),
            "tarea": tarea.dict() if tarea else None,
            "comentario": comentario.dict() if comentario else None,
        }

        # Usa IA para personalizar texto corto en el mismo orden de la plantilla
        variables = await render_body_vars_with_ai(
            contexto=contexto,
            variable_order=variable_order,
            plantilla=template_name,
            fallback=fallback,
        )

        # Asegura longitud correcta
        if len(variables) != expected_count:
            logger.warning(
                "Cantidad de variables inesperada (%s), se usa fallback",
                len(variables),
            )
            return fallback
        logger.info("Variables generadas con IA listas")
        return variables

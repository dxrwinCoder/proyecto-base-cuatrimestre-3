from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from pydantic import BaseModel, Field, validator


class NotificationEvent(str, Enum):
    """
    Tipos de eventos que disparan notificaciones.
    """

    TAREA_POR_VENCER = "tarea_por_vencer"
    NUEVA_TAREA = "nueva_tarea"
    ASIGNADO_EVENTO = "asignado_evento"
    COMENTARIO_TAREA = "comentario_tarea"
    TAREA_COMPLETADA = "tarea_completada"
    TAREA_VENCIDA = "tarea_vencida"
    CAMBIO_ESTADO_TAREA = "cambio_estado_tarea"


class Destinatario(BaseModel):
    nombre: Optional[str] = Field(None, description="Nombre visible del destinatario")
    telefono: str = Field(..., description="Numero en formato E.164")
    rol_id: int = Field(..., description="1 = admin, 2 = miembro")
    contacto: Optional[str] = Field(
        None, description="Correo o texto de contacto que va en la variable {{4}}"
    )


class ContextoTarea(BaseModel):
    id: Optional[int] = None
    titulo: Optional[str] = None
    fecha_limite: Optional[date] = None
    estado: Optional[str] = None
    descripcion: Optional[str] = None
    creador_nombre: Optional[str] = None
    asignado_nombre: Optional[str] = None
    evento_titulo: Optional[str] = None


class ContextoComentario(BaseModel):
    contenido: Optional[str] = None
    tarea_id: Optional[int] = None
    tarea_titulo: Optional[str] = None
    autor_nombre: Optional[str] = None
    fecha: Optional[datetime] = None


class NotificationPayload(BaseModel):
    """
    Payload que recibe el endpoint para enviar una notificacion de WhatsApp.
    """

    evento: NotificationEvent
    destinatario: Destinatario
    tarea: Optional[ContextoTarea] = None
    comentario: Optional[ContextoComentario] = None
    template_name: Optional[str] = Field(
        None, description="Nombre de plantilla a usar (si se quiere override)"
    )
    template_language: Optional[str] = Field(
        None, description="Codigo de idioma para la plantilla (ej. es, es_MX)"
    )
    variable_order: Optional[List[str]] = Field(
        None,
        description="Orden de variables del cuerpo, ej. ['fecha','hora'] para plantilla de 2 variables",
    )
    body_variables_expected: Optional[int] = Field(
        None, description="Cantidad esperada de variables (default toma config)"
    )
    override_variables: Optional[List[str]] = Field(
        None,
        description="Si viene, se usa directamente como variables de la plantilla en orden.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadatos opcionales para trazabilidad"
    )

    @validator("destinatario")
    def _telefono_en_e164(cls, value: Destinatario):
        if not value.telefono.startswith("+"):
            raise ValueError("telefono debe venir en formato E.164 (ej. +5215555555555)")
        return value

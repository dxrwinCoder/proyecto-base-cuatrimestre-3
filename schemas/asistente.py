from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HistorialTurno(BaseModel):
    """Representa un turno previo en la conversacion."""

    role: str
    content: str


class ConsultaIA(BaseModel):
    """Entrada basica para el asistente IA."""

    mensaje: str
    historial_conversacion: Optional[List[Dict[str, str]]] = None


class Sugerencia(BaseModel):
    """Texto corto de ayuda o alerta para el usuario."""

    texto: str
    tipo: str = "sugerencia"


class BotonAccion(BaseModel):
    """Boton/accion sugerida para el frontend."""

    texto: str
    accion: str
    parametros: Dict[str, Any] = Field(default_factory=dict)


class RespuestaIA(BaseModel):
    """Respuesta estructurada del asistente IA."""

    respuesta: str
    intencion_detectada: Optional[str] = None
    acciones_realizadas: Optional[List[str]] = None
    datos_obtenidos: Optional[Dict[str, Any]] = None
    sugerencias: Optional[List[Sugerencia]] = None
    botones_accion: Optional[List[BotonAccion]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    tipo_respuesta: str = "texto"

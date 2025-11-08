# schemas/notificacion.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class NotificacionBase(BaseModel):
    id_miembro_destino: int
    id_miembro_origen: Optional[int] = None
    id_tarea: Optional[int] = None
    id_evento: Optional[int] = None  # <-- ¡Añadido!
    tipo: str
    mensaje: str


class NotificacionCreate(NotificacionBase):
    pass


class Notificacion(NotificacionBase):
    id: int
    leido: bool
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)

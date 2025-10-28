from pydantic import BaseModel
from typing import Optional


class NotificacionBase(BaseModel):
    id_miembro_destino: int
    tipo: str
    mensaje: str


class NotificacionCreate(NotificacionBase):
    id_miembro_origen: Optional[int] = None
    id_tarea: Optional[int] = None
    id_evento: Optional[int] = None


class Notificacion(NotificacionBase):
    id: int
    leido: bool

    class Config:
        from_attributes = True

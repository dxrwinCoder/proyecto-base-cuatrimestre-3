# schemas/mensaje.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from .miembro import MiembroResponse  # Importamos una respuesta ligera


class MensajeBase(BaseModel):
    contenido: str


class MensajeCreate(MensajeBase):
    id_hogar: int
    id_remitente: int


# Schema 'ligero' del miembro para el chat
class MiembroChatResponse(BaseModel):
    id: int
    nombre_completo: str

    model_config = ConfigDict(from_attributes=True)


class Mensaje(MensajeBase):
    id: int
    id_hogar: int
    id_remitente: int
    fecha_envio: datetime

    model_config = ConfigDict(from_attributes=True)


class MensajeResponse(Mensaje):
    # ¡La magia del N+1 arreglada!
    remitente: Optional[MiembroChatResponse] = None

    model_config = ConfigDict(from_attributes=True)

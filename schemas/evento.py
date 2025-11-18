from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# from pydantic import ConfigDict


class EventoBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    fecha_hora: datetime
    duracion_min: Optional[int] = 60
    id_hogar: int
    creado_por: int


class EventoCreate(EventoBase):
    pass


class Evento(EventoBase):
    id: int

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    # class Config:
    #     orm_mode = True
    #     json_encoders = {
    #         datetime: lambda v: v.isoformat()  # <-- Soluciona el 'TypeError: Object of type datetime is not JSON serializable'
    #     }

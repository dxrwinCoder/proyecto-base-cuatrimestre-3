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


class EventoUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_hora: Optional[datetime] = None
    duracion_min: Optional[int] = None
    estado: Optional[bool] = None


class Evento(EventoBase):
    id: int
    estado: bool = True

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    # class Config:
    #     orm_mode = True
    #     json_encoders = {
    #         datetime: lambda v: v.isoformat()  # <-- Soluciona el 'TypeError: Object of type datetime is not JSON serializable'
    #     }

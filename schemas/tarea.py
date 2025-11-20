# schemas/tarea.py
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field

from .comentario_tarea import ComentarioTarea


class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    categoria: str
    fecha_limite: Optional[date] = None
    repeticion: Optional[str] = "ninguna"
    asignado_a: int
    id_hogar: int
    ubicacion: Optional[str] = None
    id_evento: Optional[int] = None


class TareaCreate(TareaBase):
    # 'creado_por' se obtiene del usuario autenticado
    pass


class TareaUpdateEstado(BaseModel):
    estado_actual: str


class Tarea(TareaBase):
    id: int
    estado: bool
    estado_actual: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    fecha_asignacion: datetime
    tiempo_total_segundos: Optional[int] = None
    creado_por: Optional[int] = None
    tiempo_transcurrido_min: Optional[int] = None
    tiempo_restante_min: Optional[int] = None
    comentarios: list[ComentarioTarea] = Field(default_factory=list)

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }

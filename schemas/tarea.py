# schemas/tarea.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from .comentario_tarea import ComentarioTarea  # Importar schema de comentario


# Asumo que esta es su TareaBase
class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    categoria: str  # Asumiendo que usa el ENUM o lo valida en otro lugar
    fecha_limite: Optional[date] = None
    repeticion: Optional[str] = "ninguna"
    asignado_a: int
    id_hogar: int
    ubicacion: Optional[str] = None
    id_evento: Optional[int] = None


class TareaCreate(TareaBase):
    # 'creado_por' no va aquí, se obtiene del token (current_user)
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

    comentarios: list[ComentarioTarea] = (
        []
    )  # <-- ¡Esto expone los comentarios en el JSON!

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }

    # model_config = ConfigDict(from_attributes=True)

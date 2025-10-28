from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    categoria: str
    tipo_tarea: str
    fecha_limite: Optional[date] = None
    repeticion: str = "ninguna"
    asignado_a: int
    id_hogar: int
    ubicacion: Optional[str] = None
    id_evento: Optional[int] = None


class TareaCreate(TareaBase):
    pass


class TareaUpdate(BaseModel):
    estado_actual: Optional[str] = None  # Solo se permite actualizar el estado
    # Otros campos no se editan una vez asignada


class Tarea(TareaBase):
    id: int
    estado_actual: str
    id_sesion_mensaje: Optional[str] = None
    tiempo_total_segundos: Optional[int] = None
    fecha_asignacion: datetime

    class Config:
        from_attributes = True

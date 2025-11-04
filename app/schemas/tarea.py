from pydantic import BaseModel
from datetime import date
from typing import Optional


class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    categoria: str  # 'limpieza', 'cocina', 'compras', 'mantenimiento'
    fecha_limite: Optional[date] = None
    repeticion: str = "ninguna"
    asignado_a: int
    id_hogar: int
    ubicacion: Optional[str] = None
    id_evento: Optional[int] = None


class TareaCreate(TareaBase):
    pass


class TareaUpdateEstado(BaseModel):
    estado_actual: str  # 'en_progreso', 'completada'


class Tarea(TareaBase):
    id: int
    estado_actual: str
    tiempo_total_segundos: Optional[int] = None
    fecha_asignacion: str

    class Config:
        from_attributes = True

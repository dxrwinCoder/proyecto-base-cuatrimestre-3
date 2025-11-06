from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import date, datetime
from typing import Optional


model_config = ConfigDict(from_attributes=True)


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
    fecha_asignacion: datetime

    @field_serializer("fecha_asignacion")
    def serialize_fecha_asignacion(self, fecha_asignacion: datetime, _info):
        """Convierte datetime a string ISO format"""
        return fecha_asignacion.isoformat() if fecha_asignacion else None


# class Config:
#     from_attributes = True

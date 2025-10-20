from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from enum import Enum

class CategoriaEnum(str, Enum):
    limpieza = "limpieza"
    cocina = "cocina"
    compras = "compras"
    mantenimiento = "mantenimiento"

class RepeticionEnum(str, Enum):
    ninguna = "ninguna"
    diaria = "diaria"
    semanal = "semanal"

class EstadoTareaEnum(str, Enum):
    pendiente = "pendiente"
    completada = "completada"

class TareaBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = None
    categoria: CategoriaEnum
    fecha_limite: Optional[date] = None
    repeticion: RepeticionEnum = RepeticionEnum.ninguna
    asignado_a: int
    ubicacion: Optional[str] = Field(None, max_length=50)

class TareaCreate(TareaBase):
    id_hogar: int

class TareaUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = None
    categoria: Optional[CategoriaEnum] = None
    fecha_limite: Optional[date] = None
    repeticion: Optional[RepeticionEnum] = None
    asignado_a: Optional[int] = None
    ubicacion: Optional[str] = Field(None, max_length=50)
    estado_tarea: Optional[EstadoTareaEnum] = None

class Tarea(TareaBase):
    id: int
    id_hogar: int
    estado_tarea: EstadoTareaEnum = EstadoTareaEnum.pendiente

    class Config:
        from_attributes = True
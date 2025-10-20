from pydantic import BaseModel
from datetime import date
from typing import Optional

class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    categoria: str
    fecha_limite: Optional[date] = None
    repeticion: str = "ninguna"
    asignado_a: int
    id_hogar: int
    ubicacion: Optional[str] = None

class TareaCreate(TareaBase):
    pass

class Tarea(TareaBase):
    id: int
    estado_tarea: str = "pendiente"

    class Config:
        from_attributes = True
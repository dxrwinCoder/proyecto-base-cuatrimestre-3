from pydantic import BaseModel
from typing import Optional

class ModuloBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = ""

class ModuloCreate(ModuloBase):
    pass

class Modulo(ModuloBase):
    id: int

    class Config:
        from_attributes = True
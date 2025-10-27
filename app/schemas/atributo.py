from pydantic import BaseModel
from typing import Optional


class AtributoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    tipo: str  # Ej: "INT", "VARCHAR", "BOOLEAN"


class AtributoCreate(AtributoBase):
    pass


class AtributoUpdate(AtributoBase):
    pass


class Atributo(AtributoBase):
    id: int

    class Config:
        from_attributes = True

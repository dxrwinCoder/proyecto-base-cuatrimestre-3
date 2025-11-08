from pydantic import BaseModel
from typing import Optional
from pydantic import ConfigDict


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

    model_config = ConfigDict(from_attributes=True)

    # class Config:
    #     from_attributes = True

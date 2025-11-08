from pydantic import BaseModel
from typing import Optional
from pydantic import ConfigDict


class ModuloBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = ""


class ModuloCreate(ModuloBase):
    pass


class Modulo(ModuloBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

    # class Config:
    #     from_attributes = True

from pydantic import BaseModel
from typing import Optional


class AtributoMiembroBase(BaseModel):
    id_miembro: int
    id_atributo: int
    valor: str


class AtributoMiembroCreate(AtributoMiembroBase):
    pass


class AtributoMiembroUpdate(BaseModel):
    valor: str


class AtributoMiembro(AtributoMiembroBase):
    id: int

    class Config:
        from_attributes = True

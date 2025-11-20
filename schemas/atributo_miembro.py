from pydantic import BaseModel
from typing import Optional
from pydantic import ConfigDict

model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)

    class Config:
        orm_mode = True

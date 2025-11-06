from pydantic import BaseModel
from typing import Optional
from pydantic import ConfigDict

model_config = ConfigDict(from_attributes=True)


class HogarBase(BaseModel):
    nombre: str


class HogarCreate(HogarBase):
    pass


class Hogar(HogarBase):
    id: int

    # class Config:
    #     from_attributes = True

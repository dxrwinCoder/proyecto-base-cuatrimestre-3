from pydantic import BaseModel
from typing import Optional

class HogarBase(BaseModel):
    nombre: str

class HogarCreate(HogarBase):
    pass

class Hogar(HogarBase):
    id: int

    class Config:
        from_attributes = True
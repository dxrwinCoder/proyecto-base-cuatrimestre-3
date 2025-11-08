# schemas/hogar.py
from pydantic import BaseModel, ConfigDict
from typing import Optional


class HogarBase(BaseModel):
    nombre: str


class HogarCreate(HogarBase):
    pass


class HogarUpdate(BaseModel):
    nombre: Optional[str] = None
    estado: Optional[bool] = None


class Hogar(HogarBase):
    id: int
    # ¡OJO! Su modelo 'Hogar' en el service usa 'estado'
    # Debería estar aquí también
    estado: bool = True

    model_config = ConfigDict(from_attributes=True)

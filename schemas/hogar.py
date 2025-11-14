# schemas/hogar.py
from pydantic import BaseModel
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
    
    class Config:
        orm_mode = True
    #esto se descomenta para usar  la version 2 de pydantic
    #model_config = ConfigDict(from_attributes=True)

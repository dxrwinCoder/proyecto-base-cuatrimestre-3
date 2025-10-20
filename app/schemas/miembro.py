from pydantic import BaseModel, EmailStr
from typing import Optional

class MiembroBase(BaseModel):
    nombre_completo: str
    correo_electronico: EmailStr
    id_rol: int
    id_hogar: int

class MiembroCreate(MiembroBase):
    contrasena: str

class Miembro(MiembroBase):
    id: int

    class Config:
        from_attributes = True
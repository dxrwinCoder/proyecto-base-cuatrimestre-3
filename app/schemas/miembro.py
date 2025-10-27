from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class MiembroBase(BaseModel):
    nombre_completo: str = Field(..., min_length=2, max_length=100)
    correo_electronico: EmailStr
    id_rol: int
    id_hogar: int


class MiembroCreate(MiembroBase):
    contrasena: str = Field(..., min_length=8, max_length=72)


class MiembroUpdate(BaseModel):
    nombre_completo: Optional[str] = Field(None, min_length=2, max_length=100)
    correo_electronico: Optional[EmailStr] = None
    id_rol: Optional[int] = None
    id_hogar: Optional[int] = None
    estado: Optional[bool] = None


class Miembro(MiembroBase):
    id: int
    estado: bool = True
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class MiembroResponse(Miembro):
    rol: Optional["RolResponse"] = None  # Cambiar a RolResponse

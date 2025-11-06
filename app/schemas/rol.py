from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import ConfigDict

model_config = ConfigDict(from_attributes=True)


class RolBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class RolCreate(RolBase):
    pass


class RolUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[bool] = None


class Rol(RolBase):
    id: int
    estado: bool = True
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    # class Config:
    #     from_attributes = True


class RolResponse(Rol):
    pass

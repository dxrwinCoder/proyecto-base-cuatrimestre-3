# schemas/rol.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# (Asegúrese de que ConfigDict NO se use aquí si es Pydantic v1)
from pydantic import BaseModel 

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

    # --- ¡PARCHE DE SINTAXIS V1! ---
    class Config:
        orm_mode = True # Reemplaza a model_config = ConfigDict(from_attributes=True)

class RolResponse(Rol):
    # Esta clase hereda el 'class Config' de Rol
    pass






# from pydantic import BaseModel
# from typing import Optional
# from datetime import datetime
# from pydantic import ConfigDict


# class RolBase(BaseModel):
#     nombre: str
#     descripcion: Optional[str] = None


# class RolCreate(RolBase):
#     pass


# class RolUpdate(BaseModel):
#     nombre: Optional[str] = None
#     descripcion: Optional[str] = None
#     estado: Optional[bool] = None


# class Rol(RolBase):
#     id: int
#     estado: bool = True
#     fecha_creacion: datetime
#     fecha_actualizacion: datetime

#     model_config = ConfigDict(from_attributes=True)  # <-- ¡VA AQUÍ ADENTRO!


# class RolResponse(Rol):
#     model_config = ConfigDict(from_attributes=True)  # <-- ¡Y AQUÍ!

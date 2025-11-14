# schemas/miembro.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
# Importar el schema que se va a referenciar
from .rol import RolResponse 

class MiembroBase(BaseModel):
    nombre_completo: str = Field(..., min_length=2, max_length=100)
    correo_electronico: EmailStr
    id_rol: int
    id_hogar: int

class MiembroCreate(MiembroBase):
    contrasena: str = Field(..., min_length=8, max_length=72)

class MiembroUpdate(BaseModel):
    # ... (sus campos de update)
    pass

class Miembro(MiembroBase):
    id: int
    estado: bool = True
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    
    # --- ¡PARCHE DE SINTAXIS V1! ---
    class Config:
        orm_mode = True

class MiembroResponse(Miembro):
    # ¡La referencia circular!
    # Usamos el tipo real, no el string, si es posible importarlo
    rol: Optional[RolResponse] = None 
    
    # (Hereda el Config.orm_mode de Miembro)





# from pydantic import BaseModel, EmailStr, Field
# from typing import Optional
# from datetime import datetime
# from pydantic import ConfigDict


# class MiembroBase(BaseModel):
#     nombre_completo: str = Field(..., min_length=2, max_length=100)
#     correo_electronico: EmailStr
#     id_rol: int
#     id_hogar: int


# class MiembroCreate(MiembroBase):
#     contrasena: str = Field(..., min_length=8, max_length=72)

#     model_config = ConfigDict(from_attributes=True)


# class MiembroUpdate(BaseModel):
#     nombre_completo: Optional[str] = Field(None, min_length=2, max_length=100)
#     correo_electronico: Optional[EmailStr] = None
#     id_rol: Optional[int] = None
#     id_hogar: Optional[int] = None
#     estado: Optional[bool] = None

#     model_config = ConfigDict(from_attributes=True)


# class Miembro(MiembroBase):
#     id: int
#     estado: bool = True
#     fecha_creacion: datetime
#     fecha_actualizacion: datetime

#     model_config = ConfigDict(from_attributes=True)

#     # class Config:
#     #     from_attributes = True


# class MiembroResponse(Miembro):
#     rol: Optional["RolResponse"] = None  # Cambiar a RolResponse

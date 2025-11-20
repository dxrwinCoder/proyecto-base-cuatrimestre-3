from pydantic import BaseModel
from typing import Optional


class PermisoBase(BaseModel):
    id_rol: int
    id_modulo: int
    puede_crear: Optional[bool] = False
    puede_leer: Optional[bool] = True
    puede_actualizar: Optional[bool] = False
    puede_eliminar: Optional[bool] = False


class PermisoCreate(PermisoBase):
    pass


class PermisoUpdate(PermisoBase):
    pass


class Permiso(PermisoBase):
    id: int

    class Config:
        orm_mode = True

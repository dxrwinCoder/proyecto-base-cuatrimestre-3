from pydantic import BaseModel
from typing import Optional


class ComentarioTareaBase(BaseModel):
    id_tarea: int
    contenido: str
    url_imagen: Optional[str] = None


class ComentarioTareaCreate(ComentarioTareaBase):
    pass


class ComentarioTarea(ComentarioTareaBase):
    id: int
    id_miembro: int

    class Config:
        from_attributes = True

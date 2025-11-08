from pydantic import BaseModel
from typing import Optional
from pydantic import ConfigDict


class ComentarioTareaCreate(BaseModel):
    id_tarea: int
    contenido: str
    url_imagen: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ComentarioTarea(ComentarioTareaCreate):
    id: int
    id_miembro: int

    model_config = ConfigDict(from_attributes=True)

    # class Config:
    #     from_attributes = True

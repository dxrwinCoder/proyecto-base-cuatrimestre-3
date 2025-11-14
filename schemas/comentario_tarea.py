from pydantic import BaseModel
from typing import Optional
#from pydantic import ConfigDict


class ComentarioTareaCreate(BaseModel):
    id_tarea: int
    contenido: str
    url_imagen: Optional[str] = None



class ComentarioTarea(ComentarioTareaCreate):
    id: int
    id_miembro: int

    class Config:
        orm_mode = True

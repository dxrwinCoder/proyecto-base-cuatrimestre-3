from pydantic import BaseModel
import models

class User(BaseModel):
    id: int
    id_rol: int
    nombre: str
    apellido: str
    cedula: str
    edad: int
    usuario: str
    contrasena: str
    #models.ForeignKey("app.models.Rol.id")
    
    

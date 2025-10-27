from pydantic import BaseModel, Field
from typing import Optional


class MiembroLogin(BaseModel):
    correo_electronico: str
    contrasena: str


class MiembroRegistro(BaseModel):
    nombre_completo: str
    correo_electronico: str
    contrasena: str = Field(
        ..., min_length=8, max_length=72
    )  # Contraseña entre 8 y 72 caracteres
    id_rol: int
    id_hogar: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # rol: str
    id_miembro: int
    id_hogar: int


# Nuevo esquema solo para Swagger UI
class OAuth2PasswordRequestFormCompat(BaseModel):
    username: str  # correo electrónico
    password: str  # contraseña

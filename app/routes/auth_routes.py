from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from utils.logger import setup_logger
from db.database import get_db
from models.miembro import Miembro
from schemas.auth import (
    MiembroLogin,
    MiembroRegistro,
    Token,
    OAuth2PasswordRequestFormCompat,
)
from services.auth_service import (
    autenticar_miembro,
    crear_miembro,
    crear_token_para_miembro,
)

logger = setup_logger("auth_routes")

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registrar_miembro(datos: MiembroRegistro, db: AsyncSession = Depends(get_db)):
    try:
        # Crear el miembro
        miembro = await crear_miembro(db, datos)

        # Cargar explícitamente el rol
        result = await db.execute(
            select(Miembro)
            .options(selectinload(Miembro.rol))
            .where(Miembro.id == miembro.id)
        )
        miembro_con_rol = result.scalar_one()

        logger.info(
            f"Miembro creado y retornado desde el servicio auth_service {miembro_con_rol}"
        )

        # Crear token con el miembro que tiene el rol cargado
        access_token = crear_token_para_miembro(miembro_con_rol)

        return Token(
            access_token=access_token,
            rol=miembro_con_rol.rol.nombre,
            id_miembro=miembro_con_rol.id,
            id_hogar=miembro_con_rol.id_hogar,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(datos: MiembroLogin, db: AsyncSession = Depends(get_db)):
    miembro = await autenticar_miembro(db, datos.correo_electronico, datos.contrasena)
    if not miembro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
        )
    access_token = crear_token_para_miembro(miembro)
    return Token(
        access_token=access_token,
        rol=miembro.rol,
        id_miembro=miembro.id,
        id_hogar=miembro.id_hogar,
    )


# Nueva ruta SOLO para Swagger UI (no la uses en producción)
@router.post("/login-swagger", response_model=Token, include_in_schema=False)
async def login_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    # Mapea username → correo_electronico, password → contrasena
    miembro = await autenticar_miembro(db, form_data.username, form_data.password)
    if not miembro:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    access_token = crear_token_para_miembro(miembro)
    return Token(
        access_token=access_token,
        rol=miembro.rol,
        id_miembro=miembro.id,
        id_hogar=miembro.id_hogar,
    )

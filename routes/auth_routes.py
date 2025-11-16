from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from utils.logger import setup_logger
from db.database import get_db
from schemas.auth import MiembroLogin, MiembroRegistro, Token
from schemas.miembro import MiembroResponse
from services.auth_service import (
    autenticar_miembro,
    crear_miembro,
    crear_token_para_miembro,
)

logger = setup_logger("auth_routes")

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=Token, status_code=status.HTTP_201_CREATED)
async def registrar_miembro(datos: MiembroRegistro, db: AsyncSession = Depends(get_db)):
    """
    Ruta "calibrada" para registrar un miembro.
    Maneja la transacción (commit/rollback).
    """
    try:
        # 1. Llamar al servicio (que usa flush)
        # 'miembro_modelo' es un objeto SQLAlchemy
        miembro_modelo = await crear_miembro(db, datos)

        # 2. Si todo sale bien, la RUTA hace commit
        await db.commit()

        # Refrescar el objeto después del commit para asegurar que todas
        # las relaciones (como el nuevo hogar) estén cargadas.
        await db.refresh(miembro_modelo.hogar)

        logger.info(
            f"Miembro creado y transacción confirmada: {miembro_modelo.correo_electronico}"
        )

        # 3. Crear y devolver el token
        # El servicio 'crear_token_para_miembro' espera un objeto Miembro (que ya tenemos)
        token_jwt = crear_token_para_miembro(miembro_modelo)

        # Convertir el modelo SQLAlchemy (miembro_modelo) al schema Pydantic (MiembroResponse)
        # Usamos .from_orm() porque su entorno está en Pydantic v1
        miembro_schema = MiembroResponse.from_orm(miembro_modelo)

        return Token(
            access_token=token_jwt,
            id_miembro=miembro_schema.id,
            id_hogar=miembro_schema.id_hogar,
            rol=miembro_schema.rol,  # Pasamos el objeto RolResponse
        )

    except ValueError as e:
        await db.rollback()
        logger.warning(f"Error de validación al registrar miembro: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error interno al registrar miembro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al registrar el miembro.",
        )


@router.post("/login", response_model=Token)
async def login(datos: MiembroLogin, db: AsyncSession = Depends(get_db)):

    miembro = await autenticar_miembro(db, datos.correo_electronico, datos.contrasena)
    if not miembro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectas",
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

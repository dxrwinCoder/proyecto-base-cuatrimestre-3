from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.auth import MiembroLogin, MiembroRegistro, Token
from services.auth_service import autenticar_miembro, crear_miembro, crear_token_para_miembro

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registrar_miembro(datos: MiembroRegistro, db: AsyncSession = Depends(get_db)):
    try:
        miembro = await crear_miembro(db, datos)
        access_token = crear_token_para_miembro(miembro)
        return Token(
            access_token=access_token,
            rol=miembro.rol,
            id_miembro=miembro.id,
            id_hogar=miembro.id_hogar
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(datos: MiembroLogin, db: AsyncSession = Depends(get_db)):
    miembro = await autenticar_miembro(db, datos.correo_electronico, datos.contrasena)
    if not miembro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    access_token = crear_token_para_miembro(miembro)
    return Token(
        access_token=access_token,
        rol=miembro.rol,
        id_miembro=miembro.id,
        id_hogar=miembro.id_hogar
    )
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from models.miembro import Miembro
from config.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def obtener_miembro_actual(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        miembro_id: str = payload.get("sub")
        if miembro_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    miembro = await db.get(Miembro, int(miembro_id))
    if miembro is None or not miembro.estado:
        raise credentials_exception
    return miembro
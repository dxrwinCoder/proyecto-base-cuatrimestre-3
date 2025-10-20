from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from utils.auth import obtener_miembro_actual
from services.permiso_service import verificar_permiso

def require_permission(modulo_nombre: str, accion: str):
    async def _wrapper(
        current_user = Depends(obtener_miembro_actual),
        db: AsyncSession = Depends(get_db)
    ):
        if not await verificar_permiso(db, current_user.id, modulo_nombre, accion):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción"
            )
        return current_user
    return _wrapper
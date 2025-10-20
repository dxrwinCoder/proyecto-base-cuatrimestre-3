from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.permiso import PermisoCreate
from services.permiso_service import asignar_permiso 

router = APIRouter(prefix="/permisos", tags=["Permisos"])

@router.post("/")
async def crear_permiso(permiso: PermisoCreate, db: AsyncSession = Depends(get_db)):
    return await asignar_permiso(db, permiso.model_dump())
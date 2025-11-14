from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.modulo import ModuloCreate, Modulo
from services.modulo_service import crear_modulo

router = APIRouter(prefix="/modulos", tags=["Módulos"])

@router.post("/", response_model=Modulo)
async def crear_modulo_endpoint(modulo: ModuloCreate, db: AsyncSession = Depends(get_db)):
    return await crear_modulo(db, modulo.nombre, modulo.descripcion)

# @router.get("/{modulo_id}", response_model=Modulo)
# async def ver_modulo(modulo_id: int, db: AsyncSession = Depends(get_db)):
#     modulo = await obtener_modulo(db, modulo_id)
#     if not modulo:
#         raise HTTPException(status_code=404, detail="Módulo no encontrado")
#     return modulo

# @router.get("/", response_model=list[Modulo])
# async def listar_modulos(db: AsyncSession = Depends(get_db)):
#     return await listar_modulos_activos(db)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.modulo import ModuloCreate, Modulo
from services.modulo_service import crear_modulo
from utils.permissions import require_permission
from models.miembro import Miembro

router = APIRouter(prefix="/modulos", tags=["Módulos"])

@router.post("/", response_model=Modulo, status_code=status.HTTP_201_CREATED)
async def crear_modulo_endpoint(
    modulo: ModuloCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Modulos", "crear")),
):
    try:
        resultado = await crear_modulo(db, modulo.nombre, modulo.descripcion)
        await db.commit()
        return resultado
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear módulo: {str(e)}",
        )

# @router.get("/{modulo_id}", response_model=Modulo)
# async def ver_modulo(modulo_id: int, db: AsyncSession = Depends(get_db)):
#     modulo = await obtener_modulo(db, modulo_id)
#     if not modulo:
#         raise HTTPException(status_code=404, detail="Módulo no encontrado")
#     return modulo

# @router.get("/", response_model=list[Modulo])
# async def listar_modulos(db: AsyncSession = Depends(get_db)):
#     return await listar_modulos_activos(db)

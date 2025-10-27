from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.atributo_miembro import AtributoMiembroCreate, AtributoMiembro
from services.atributo_miembro_service import *

router = APIRouter(prefix="/atributo-miembro", tags=["Atributos de Miembros"])


@router.post("/", response_model=AtributoMiembro)
async def asignar_atributo(
    data: AtributoMiembroCreate, db: AsyncSession = Depends(get_db)
):
    resultado = await asignar_atributo_a_miembro(
        db, data.id_miembro, data.id_atributo, data.valor
    )
    if not resultado:
        raise HTTPException(400, "Miembro o atributo no válido")
    return resultado


@router.get("/miembro/{id_miembro}", response_model=list[AtributoMiembro])
async def ver_atributos_de_miembro(id_miembro: int, db: AsyncSession = Depends(get_db)):
    return await obtener_atributos_de_miembro(db, id_miembro)


@router.post("/buscar", response_model=list)
async def buscar_miembros(filtros: dict, db: AsyncSession = Depends(get_db)):
    """
    Ejemplo de cuerpo:
    {
    "atributos": {"edad": "12", "nivel_responsabilidad": "bajo"},
    "nombre": "Juan",
    "id_hogar": 1
    }
    """
    miembros = await buscar_miembros_por_atributos(db, filtros)
    return miembros

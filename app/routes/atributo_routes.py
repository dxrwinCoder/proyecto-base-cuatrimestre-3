from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.atributo import AtributoCreate, AtributoUpdate, Atributo
from services.atributo_service import *

router = APIRouter(prefix="/atributos", tags=["Atributos"])


@router.post("/", response_model=Atributo)
async def crear_atributo_endpoint(
    atributo: AtributoCreate, db: AsyncSession = Depends(get_db)
):
    return await crear_atributo(
        db, atributo.nombre, atributo.descripcion, atributo.tipo
    )


@router.get("/{atributo_id}", response_model=Atributo)
async def ver_atributo(atributo_id: int, db: AsyncSession = Depends(get_db)):
    attr = await obtener_atributo(db, atributo_id)
    if not attr or not attr.estado:
        raise HTTPException(404, "Atributo no encontrado")
    return attr


@router.get("/", response_model=list[Atributo])
async def listar_atributos(db: AsyncSession = Depends(get_db)):
    return await listar_atributos_activos(db)


@router.put("/{atributo_id}", response_model=Atributo)
async def actualizar_atributo_endpoint(
    atributo_id: int, updates: AtributoUpdate, db: AsyncSession = Depends(get_db)
):
    attr = await actualizar_atributo(db, atributo_id, updates.model_dump())
    if not attr:
        raise HTTPException(404, "Atributo no encontrado")
    return attr


@router.delete("/{atributo_id}")
async def eliminar_atributo(atributo_id: int, db: AsyncSession = Depends(get_db)):
    if not await eliminar_atributo_logico(db, atributo_id):
        raise HTTPException(404, "Atributo no encontrado")
    return {"mensaje": "Atributo desactivado"}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.atributo import (
    AtributoCreate,
    AtributoUpdate,
    Atributo as AtributoSchema,
)
from services.atributo_service import (
    crear_atributo,
    obtener_atributo,
    listar_atributos_activos,
    actualizar_atributo,
    eliminar_atributo_logico,
)
from utils.permissions import require_permission
from models.miembro import Miembro

router = APIRouter(prefix="/atributos", tags=["Atributos"])


@router.post("/", response_model=AtributoSchema, status_code=status.HTTP_201_CREATED)
async def crear_atributo_endpoint(
    atributo: AtributoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Atributos", "crear")),
):
    try:
        resultado = await crear_atributo(
            db, atributo.nombre, atributo.descripcion, atributo.tipo
        )
        await db.commit()
        return resultado
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear atributo: {str(e)}",
        )


@router.get("/{atributo_id}", response_model=AtributoSchema)
async def ver_atributo(
    atributo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Atributos", "leer")),
):
    attr = await obtener_atributo(db, atributo_id)
    if not attr or not attr.estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo no encontrado")
    return attr


@router.get("/", response_model=list[AtributoSchema])
async def listar_atributos(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Atributos", "leer")),
):
    return await listar_atributos_activos(db)


@router.put("/{atributo_id}", response_model=AtributoSchema)
async def actualizar_atributo_endpoint(
    atributo_id: int,
    updates: AtributoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Atributos", "actualizar")),
):
    try:
        # Para Pydantic v1 usamos .dict(exclude_unset=True)
        attr = await actualizar_atributo(db, atributo_id, updates.dict(exclude_unset=True))
        if not attr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo no encontrado")
        await db.commit()
        return attr
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar atributo: {str(e)}",
        )


@router.delete("/{atributo_id}")
async def eliminar_atributo(
    atributo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Atributos", "eliminar")),
):
    try:
        if not await eliminar_atributo_logico(db, atributo_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo no encontrado")
        await db.commit()
        return {"mensaje": "Atributo desactivado"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar atributo: {str(e)}",
        )

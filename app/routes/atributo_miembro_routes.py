from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.atributo_miembro import AtributoMiembroCreate, AtributoMiembro
from models.miembro import Miembro
from services.atributo_miembro_service import (
    asignar_atributo_a_miembro,
    buscar_miembros_por_atributos,
    obtener_atributos_de_miembro,
)

from utils.permissions import require_permission

router = APIRouter(prefix="/atributo-miembro", tags=["Atributos de Miembros"])


@router.post("/", response_model=AtributoMiembro, status_code=status.HTTP_201_CREATED)
async def asignar_atributo(
    data: AtributoMiembroCreate,
    db: AsyncSession = Depends(get_db),
    # --- ¡AÑADIR SEGURIDAD! ---
    current_user: Miembro = Depends(
        require_permission("AtributosMiembros", "crear")
    ),  # ¡Asumiendo que el módulo se llama así!
):
    try:
        # ¡Ahora le pasamos el schema directo!
        resultado = await asignar_atributo_a_miembro(db, data)

        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Miembro o atributo no válido",
            )

        await db.commit()  # <-- ¡LA RUTA HACE COMMIT!
        return resultado
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/miembro/{id_miembro}", response_model=list[AtributoMiembro])
async def ver_atributos_de_miembro(
    id_miembro: int,
    db: AsyncSession = Depends(get_db),
    # --- ¡AÑADIR SEGURIDAD! ---
    current_user: Miembro = Depends(require_permission("AtributosMiembros", "leer")),
):
    return await obtener_atributos_de_miembro(db, id_miembro)


@router.post(
    "/buscar", response_model=list
)  # ¡Este debe ser un schema de MiembroResponse!
async def buscar_miembros(
    filtros: dict,
    db: AsyncSession = Depends(get_db),
    # --- ¡AÑADIR SEGURIDAD! ---
    current_user: Miembro = Depends(require_permission("Miembros", "leer")),
):
    miembros = await buscar_miembros_por_atributos(db, filtros)
    return miembros

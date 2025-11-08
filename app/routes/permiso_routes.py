# routes/permiso_routes.py
from fastapi import APIRouter, Depends, HTTPException, status  # <-- ¡Importar!
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.permiso import PermisoCreate, Permiso  # <-- ¡Importar Permiso!
from services.permiso_service import asignar_permiso

# --- ¡AÑADIR ESTAS IMPORTACIONES DE SEGURIDAD! ---
from models.miembro import Miembro
from utils.permissions import require_permission

# --- FIN DE IMPORTACIONES ---

router = APIRouter(prefix="/permisos", tags=["Permisos"])


@router.post(
    "/", response_model=Permiso, status_code=status.HTTP_201_CREATED
)  # <-- 201
async def crear_permiso(
    permiso: PermisoCreate,
    db: AsyncSession = Depends(get_db),
    # --- ¡AÑADIR SEGURIDAD! ---
    current_user: Miembro = Depends(require_permission("Permisos", "crear")),
):
    try:
        # ¡Usamos el schema, no el model_dump()!
        resultado = await asignar_permiso(db, permiso)

        await db.commit()  # <-- ¡LA RUTA HACE COMMIT!

        return resultado
    except ValueError as e:  # Capturar el error de duplicado
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()  # <-- ¡LA RUTA HACE ROLLBACK!
        raise HTTPException(
            status_code=500, detail=f"Error interno al asignar permiso: {str(e)}"
        )

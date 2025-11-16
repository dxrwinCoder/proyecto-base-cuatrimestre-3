# routes/ranking_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from models.miembro import Miembro
from utils.permissions import require_permission
from services.ranking_service import obtener_ranking_hogar
from schemas.ranking import RankingEntry  # ¡Importar el schema!
from utils.auth import obtener_miembro_actual
from utils.logger import setup_logger

logger = setup_logger("ranking_routes")

router = APIRouter(prefix="/ranking", tags=["Ranking y Gamificación"])


@router.get(
    "/hogar/{hogar_id}",
    response_model=list[RankingEntry],
    dependencies=[Depends(require_permission("Ranking", "leer"))],  # Protegido
)
async def get_ranking_semanal_hogar(
    hogar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    """
    Obtiene el ranking (basado en tareas completadas)
    de la semana actual para un hogar.
    """
    try:
        # Verificación de seguridad: solo puede ver el ranking de su propio hogar
        if current_user.id_hogar != hogar_id:
            logger.warning(
                f"Usuario {current_user.id} intentó ver ranking de hogar {hogar_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes ver el ranking de este hogar",
            )

        ranking = await obtener_ranking_hogar(db, hogar_id)

        # ¡Importante! Pydantic v1 requiere conversión explícita
        ranking_response = [RankingEntry.from_orm(entry) for entry in ranking]

        return ranking_response

    except Exception as e:
        logger.error(f"Error al obtener ranking del hogar {hogar_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener el ranking",
        )

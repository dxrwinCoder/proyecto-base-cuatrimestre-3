from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.comentario_tarea import ComentarioTareaCreate, ComentarioTarea
from services.comentario_tarea_service import agregar_comentario_a_tarea
from utils.auth import obtener_miembro_actual

router = APIRouter(prefix="/comentarios", tags=["Comentarios"])


@router.post("/", response_model=ComentarioTarea)
async def agregar_comentario(
    comentario: ComentarioTareaCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(obtener_miembro_actual),
):
    comentario_dict = comentario.model_dump()
    comentario_dict["id_miembro"] = current_user.id
    return await agregar_comentario_a_tarea(db, comentario_dict)

# routes/comentario_tarea_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from models.miembro import Miembro
from utils.auth import obtener_miembro_actual
from utils.permissions import require_permission
from utils.logger import setup_logger

# --- ¡LOS IMPORTS "CALIBRADOS"! ---
from schemas.comentario_tarea import ComentarioTareaCreate, ComentarioTarea
# ¡Importamos la función MODERNA desde TAREA_SERVICE!
from services.tarea_service import agregar_comentario_a_tarea, obtener_tarea_por_id

logger = setup_logger("comentario_tarea_routes")

# Asignamos un prefijo y tag
router = APIRouter(prefix="/comentarios-tarea", tags=["Comentarios y Evidencia"])


@router.post(
    "/",
    response_model=ComentarioTarea,
    status_code=status.HTTP_201_CREATED,
    # Protegemos el endpoint. Asumimos que el permiso se llama "leer" Tareas
    # ya que si puedes verla, puedes comentarla.
    dependencies=[Depends(require_permission("Tareas", "leer"))], 
)
async def crear_comentario_endpoint(
    comentario_data: ComentarioTareaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    """
    Crea un nuevo comentario en una tarea.
    Implementa la lógica de Unidad de Trabajo (Commit/Rollback).
    """
    try:
        # --- Lógica de Seguridad (Nivel de Sr.) ---
        # 1. Verificar que la tarea exista
        tarea = await obtener_tarea_por_id(db, comentario_data.id_tarea)
        if not tarea:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe.")
        
        # 2. Verificar que el usuario pertenece al mismo hogar de la tarea
        if tarea.id_hogar != current_user.id_hogar:
            logger.warning(
                f"Intento no autorizado de comentar en tarea de otro hogar por usuario {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para comentar en esta tarea."
            )
        
        # --- Lógica de Negocio (Llamada al Servicio) ---
        # Llamamos al servicio "calibrado" de 'tarea_service'
        # Le pasamos el schema y el ID del usuario que comenta
        comentario_creado = await agregar_comentario_a_tarea(
            db, 
            data=comentario_data, 
            miembro_id=current_user.id
        )
        
        # --- Unidad de Trabajo (Commit) ---
        # Si el servicio (con 'flush') y las notificaciones funcionaron,
        # la ruta "graba en piedra" la transacción.
        await db.commit()
        
        return comentario_creado

    except (ValueError, Exception) as e:
        # --- Unidad de Trabajo (Rollback) ---
        await db.rollback()
        logger.error(f"Error al crear comentario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al crear el comentario: {str(e)}"
        )

# (Aquí también debe añadir la ruta GET para listar los comentarios)
@router.get(
    "/tarea/{tarea_id}",
    response_model=list[ComentarioTarea],
    dependencies=[Depends(require_permission("Tareas", "leer"))],
)
async def listar_comentarios_por_tarea(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    """
    Obtiene todos los comentarios de una tarea específica.
    (Requiere una función 'obtener_comentarios_por_tarea' en su servicio).
    """
    # (Lógica de seguridad similar: verificar que la tarea existe y es del hogar)
    tarea = await obtener_tarea_por_id(db, tarea_id)
    if not tarea or tarea.id_hogar != current_user.id_hogar:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    # [IMPLEMENTACIÓN PENDIENTE]
    # Necesitará una función en su 'tarea_service' o un nuevo 
    # 'comentario_service' (limpio) que haga:
    # stmt = select(ComentarioTarea).where(ComentarioTarea.id_tarea == tarea_id, ComentarioTarea.estado == True)
    # result = await db.execute(stmt)
    # return result.scalars().all()
    
    # Por ahora, devolvemos una lista vacía como placeholder
    logger.warning(f"Endpoint GET /comentarios-tarea/tarea/{tarea_id} necesita implementar el servicio de listado.")
    return []





# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from db.database import get_db
# from schemas.comentario_tarea import ComentarioTareaCreate, ComentarioTarea
# from services.comentario_tarea_service import agregar_comentario_a_tarea
# from utils.auth import obtener_miembro_actual

# router = APIRouter(prefix="/comentarios", tags=["Comentarios"])


# @router.post("/", response_model=ComentarioTarea)
# async def agregar_comentario(
#     comentario: ComentarioTareaCreate,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(obtener_miembro_actual),
# ):
#     comentario_dict = comentario.model_dump()
#     comentario_dict["id_miembro"] = current_user.id
#     return await agregar_comentario_a_tarea(db, comentario_dict)

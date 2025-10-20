from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.tarea import TareaCreate, Tarea
from services.tarea_service import crear_tarea, listar_tareas_por_hogar
from utils.permissions import require_permission

router = APIRouter(prefix="/tareas", tags=["Tareas"])

@router.post("/", response_model=Tarea, dependencies=[Depends(require_permission("Tareas", "crear"))])
async def crear_tarea_endpoint(tarea: TareaCreate, db: AsyncSession = Depends(get_db)):
    return await crear_tarea(db, tarea.model_dump())

@router.get("/", response_model=list[Tarea], dependencies=[Depends(require_permission("Tareas", "leer"))])
async def listar_tareas(db: AsyncSession = Depends(get_db), user = Depends(require_permission("Tareas", "leer"))):
    return await listar_tareas_por_hogar(db, user.id_hogar)
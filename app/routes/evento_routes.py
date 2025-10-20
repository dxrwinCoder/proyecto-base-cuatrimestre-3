from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.evento import EventoCreate, Evento
from services.evento_service import crear_evento, listar_eventos_por_hogar

router = APIRouter(prefix="/eventos", tags=["Eventos"])

@router.post("/", response_model=Evento)
async def crear_evento_endpoint(evento: EventoCreate, db: AsyncSession = Depends(get_db)):
    return await crear_evento(db, evento.model_dump())

# @router.get("/{evento_id}", response_model=Evento)
# async def ver_evento(evento_id: int, db: AsyncSession = Depends(get_db)):
#     evento = await obtener_evento(db, evento_id)
#     if not evento:
#         raise HTTPException(status_code=404, detail="Evento no encontrado")
#     return evento

@router.get("/hogar/{hogar_id}", response_model=list[Evento])
async def listar_eventos_por_hogar(hogar_id: int, db: AsyncSession = Depends(get_db)):
    return await listar_eventos_por_hogar(db, hogar_id)
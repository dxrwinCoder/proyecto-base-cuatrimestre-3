from sqlalchemy.ext.asyncio import AsyncSession
from models.evento import Evento

async def crear_evento(db: AsyncSession, data: dict):
    evento = Evento(**data)
    db.add(evento)
    await db.commit()
    await db.refresh(evento)
    return evento

async def listar_eventos_por_hogar(db: AsyncSession, hogar_id: int):
    from sqlalchemy import select
    stmt = select(Evento).where(Evento.id_hogar == hogar_id, Evento.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()
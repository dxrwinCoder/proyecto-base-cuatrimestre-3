from sqlalchemy.ext.asyncio import AsyncSession
from models.mensaje import Mensaje

async def crear_mensaje(db: AsyncSession, data: dict):
    mensaje = Mensaje(**data)
    db.add(mensaje)
    await db.commit()
    await db.refresh(mensaje)
    return mensaje

async def obtener_mensajes_por_hogar(db: AsyncSession, hogar_id: int):
    from sqlalchemy import select
    stmt = select(Mensaje).where(Mensaje.id_hogar == hogar_id, Mensaje.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()
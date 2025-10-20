from sqlalchemy.ext.asyncio import AsyncSession
from models.tarea import Tarea

async def crear_tarea(db: AsyncSession, data: dict):
    tarea = Tarea(**data)
    db.add(tarea)
    await db.commit()
    await db.refresh(tarea)
    return tarea

async def listar_tareas_por_hogar(db: AsyncSession, hogar_id: int):
    from sqlalchemy import select
    stmt = select(Tarea).where(Tarea.id_hogar == hogar_id, Tarea.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()

async def marcar_completada(db: AsyncSession, tarea_id: int):
    tarea = await db.get(Tarea, tarea_id)
    if tarea and tarea.estado:
        tarea.estado_tarea = "completada"
        await db.commit()
        return tarea
    return None

async def eliminar_tarea_logico(db: AsyncSession, tarea_id: int):
    tarea = await db.get(Tarea, tarea_id)
    if tarea and tarea.estado:
        tarea.estado = False
        await db.commit()
        return True
    return False
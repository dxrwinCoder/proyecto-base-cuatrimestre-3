from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.atributo import Atributo


async def crear_atributo(db: AsyncSession, nombre: str, descripcion: str, tipo: str):
    """
    Crea un atributo pero deja el commit a la ruta llamante.
    De esta forma varias operaciones pueden agruparse en una sola transacción.
    """
    atributo = Atributo(nombre=nombre, descripcion=descripcion, tipo=tipo)
    db.add(atributo)
    await db.flush()
    await db.refresh(atributo)
    return atributo


async def obtener_atributo(db: AsyncSession, atributo_id: int):
    return await db.get(Atributo, atributo_id)


async def listar_atributos_activos(db: AsyncSession):
    stmt = select(Atributo).where(Atributo.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()


async def actualizar_atributo(db: AsyncSession, atributo_id: int, updates: dict):
    atributo = await db.get(Atributo, atributo_id)
    if atributo and atributo.estado:
        for k, v in updates.items():
            setattr(atributo, k, v)
        await db.flush()
        return atributo
    return None


async def eliminar_atributo_logico(db: AsyncSession, atributo_id: int):
    atributo = await db.get(Atributo, atributo_id)
    if atributo and atributo.estado:
        atributo.estado = False
        await db.flush()
        return True
    return False

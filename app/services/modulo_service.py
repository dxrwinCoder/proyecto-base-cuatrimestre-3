from sqlalchemy.ext.asyncio import AsyncSession
from models.modulo import Modulo


async def crear_modulo(db: AsyncSession, nombre: str, descripcion: str = ""):
    modulo = Modulo(nombre=nombre, descripcion=descripcion)
    db.add(modulo)
    await db.commit()
    await db.refresh(modulo)
    return modulo

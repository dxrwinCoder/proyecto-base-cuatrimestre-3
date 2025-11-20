from sqlalchemy.ext.asyncio import AsyncSession
from models.modulo import Modulo


async def crear_modulo(db: AsyncSession, nombre: str, descripcion: str = ""):
    """
    Crea un módulo y deja el commit a la capa de rutas para mantener transacciones consistentes.
    """
    modulo = Modulo(nombre=nombre, descripcion=descripcion)
    db.add(modulo)
    await db.flush()
    await db.refresh(modulo)
    return modulo

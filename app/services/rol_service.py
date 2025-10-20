from sqlalchemy.ext.asyncio import AsyncSession
from models.rol import Rol

async def crear_rol(db: AsyncSession, nombre: str, descripcion: str = ""):
    rol = Rol(nombre=nombre, descripcion=descripcion)
    db.add(rol)
    await db.commit()
    await db.refresh(rol)
    return rol

async def obtener_rol(db: AsyncSession, rol_id: int):
    return await db.get(Rol, rol_id)

# (métodos similares para listar, actualizar, eliminar lógico)
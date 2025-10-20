from sqlalchemy.ext.asyncio import AsyncSession
from models.miembro import Miembro
from utils.security import obtener_hash_contrasena

async def crear_miembro(db: AsyncSession, data: dict):
    miembro = Miembro(
        nombre_completo=data["nombre_completo"],
        correo_electronico=data["correo_electronico"],
        contrasena_hash=obtener_hash_contrasena(data["contrasena"]),
        id_rol=data["id_rol"],
        id_hogar=data["id_hogar"]
    )
    db.add(miembro)
    await db.commit()
    await db.refresh(miembro)
    return miembro

async def obtener_miembro(db: AsyncSession, miembro_id: int):
    return await db.get(Miembro, miembro_id)

async def listar_miembros_activos_por_hogar(db: AsyncSession, hogar_id: int):
    from sqlalchemy import select
    stmt = select(Miembro).where(Miembro.id_hogar == hogar_id, Miembro.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()

async def desactivar_miembro(db: AsyncSession, miembro_id: int):
    miembro = await db.get(Miembro, miembro_id)
    if miembro and miembro.estado:
        miembro.estado = False
        await db.commit()
        return True
    return False
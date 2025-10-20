from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.permiso import Permiso
from models.miembro import Miembro  # ← Importado aquí
from models.rol import Rol
from models.modulo import Modulo

# ✅ Nombre actualizado a 'asignar_permiso'
async def asignar_permiso(db: AsyncSession, data: dict):
    permiso = Permiso(**data)
    db.add(permiso)
    await db.commit()
    await db.refresh(permiso)
    return permiso

async def obtener_permisos_por_rol(db: AsyncSession, rol_id: int):
    stmt = select(Permiso).where(Permiso.id_rol == rol_id, Permiso.estado == True)
    result = await db.execute(stmt)
    return result.scalars().all()

async def actualizar_permiso(db: AsyncSession, permiso_id: int, updates: dict):
    permiso = await db.get(Permiso, permiso_id)
    if permiso and permiso.estado:
        for k, v in updates.items():
            setattr(permiso, k, v)
        await db.commit()
        return permiso
    return None

async def verificar_permiso(db: AsyncSession, id_miembro: int, modulo_nombre: str, accion: str):
    miembro = await db.get(Miembro, id_miembro)  # ✅ Ahora usa la clase Miembro
    if not miembro or not miembro.estado:
        return False

    stmt = (
        select(Permiso)
        .join(Rol, Permiso.id_rol == Rol.id)
        .join(Modulo, Permiso.id_modulo == Modulo.id)
        .where(
            Rol.id == miembro.id_rol,
            Modulo.nombre == modulo_nombre,
            Permiso.estado == True
        )
    )
    result = await db.execute(stmt)
    permiso = result.scalar_one_or_none()
    if not permiso:
        return False
    return getattr(permiso, f"puede_{accion}", False)
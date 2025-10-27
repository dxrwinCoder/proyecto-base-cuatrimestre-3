from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models.atributo_miembro import AtributoMiembro
from models.miembro import Miembro
from models.atributo import Atributo


async def asignar_atributo_a_miembro(
    db: AsyncSession, id_miembro: int, id_atributo: int, valor: str
):
    # Verificar que existan
    miembro = await db.get(Miembro, id_miembro)
    atributo = await db.get(Atributo, id_atributo)
    if not miembro or not atributo or not miembro.estado or not atributo.estado:
        return None

    # Crear o actualizar
    stmt = select(AtributoMiembro).where(
        AtributoMiembro.id_miembro == id_miembro,
        AtributoMiembro.id_atributo == id_atributo,
    )
    result = await db.execute(stmt)
    existente = result.scalar_one_or_none()

    if existente:
        existente.valor = valor
        existente.estado = True
    else:
        existente = AtributoMiembro(
            id_miembro=id_miembro, id_atributo=id_atributo, valor=valor
        )
        db.add(existente)

    await db.commit()
    await db.refresh(existente)
    return existente


async def obtener_atributos_de_miembro(db: AsyncSession, id_miembro: int):
    stmt = select(AtributoMiembro).where(
        AtributoMiembro.id_miembro == id_miembro, AtributoMiembro.estado == True
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def buscar_miembros_por_atributos(db: AsyncSession, filtros: dict):
    """
    filtros = {
        "atributos": {"edad": "12", "nivel_responsabilidad": "bajo"},
        "nombre": "Juan",
        "id_hogar": 1
    }
    """
    # Subconsulta: miembros que cumplen TODOS los atributos
    subq = select(AtributoMiembro.id_miembro)
    conditions = []
    for nombre_atributo, valor in filtros.get("atributos", {}).items():
        sub_subq = (
            select(AtributoMiembro.id_miembro)
            .join(Atributo, AtributoMiembro.id_atributo == Atributo.id)
            .where(
                Atributo.nombre == nombre_atributo,
                AtributoMiembro.valor == valor,
                AtributoMiembro.estado == True,
                Atributo.estado == True,
            )
        )
        conditions.append(sub_subq.exists())

    if conditions:
        subq = subq.where(and_(*conditions))

    # Consulta principal
    stmt = select(Miembro).where(Miembro.estado == True)

    if "id_hogar" in filtros:
        stmt = stmt.where(Miembro.id_hogar == filtros["id_hogar"])

    if "nombre" in filtros:
        stmt = stmt.where(Miembro.nombre_completo.like(f"%{filtros['nombre']}%"))

    if filtros.get("atributos"):
        subquery = subq.subquery()
        stmt = stmt.where(Miembro.id.in_(select(subquery.c.id_miembro)))

    result = await db.execute(stmt)
    return result.scalars().all()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.sql.expression import func
from models.atributo_miembro import AtributoMiembro
from models.miembro import Miembro
from models.atributo import Atributo
from schemas.atributo_miembro import AtributoMiembroCreate


async def asignar_atributo_a_miembro(
    db: AsyncSession, data: AtributoMiembroCreate  # <-- ¡Recibe el schema!
):
    # Verificar que existan
    miembro = await db.get(Miembro, data.id_miembro)
    atributo = await db.get(Atributo, data.id_atributo)
    if not miembro or not atributo or not miembro.estado or not atributo.estado:
        return None

    # Crear o actualizar
    stmt = select(AtributoMiembro).where(
        AtributoMiembro.id_miembro == data.id_miembro,
        AtributoMiembro.id_atributo == data.id_atributo,
    )
    result = await db.execute(stmt)
    existente = result.scalar_one_or_none()

    if existente:
        existente.valor = data.valor
        existente.estado = True
    else:
        existente = AtributoMiembro(
            id_miembro=data.id_miembro, id_atributo=data.id_atributo, valor=data.valor
        )
        db.add(existente)

    await db.flush()  # <-- ¡CAMBIO! de commit a flush
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

    # Consulta principal
    stmt = select(Miembro).where(Miembro.estado == True)

    if "id_hogar" in filtros:
        stmt = stmt.where(Miembro.id_hogar == filtros["id_hogar"])

    if "nombre" in filtros:
        stmt = stmt.where(Miembro.nombre_completo.like(f"%{filtros['nombre']}%"))

    atributos = filtros.get("atributos", {})
    if atributos:
        # 1. Crear una lista de condiciones 'OR' para los atributos
        # (Ej: (Atributo.nombre == 'Edad' AND valor == '30') OR (Atributo.nombre == 'Color' AND valor == 'Azul'))
        conditions_or = []
        for nombre_atributo, valor in atributos.items():
            conditions_or.append(
                and_(
                    Atributo.nombre == nombre_atributo,
                    AtributoMiembro.valor == valor,
                    AtributoMiembro.estado == True,
                    Atributo.estado == True,
                )
            )

        # 2. Crear la subconsulta con GROUP BY y HAVING COUNT
        # Esta subconsulta nos da los IDs de los miembros que cumplen
        # TODOS los atributos que pedimos.
        subq = (
            select(AtributoMiembro.id_miembro)
            .join(Atributo, AtributoMiembro.id_atributo == Atributo.id)
            .where(or_(*conditions_or))  # Filtra por CUALQUIERA de los atributos
            .group_by(AtributoMiembro.id_miembro)
            .having(
                func.count(AtributoMiembro.id_miembro) == len(atributos)
            )  # Se asegura que cumpla TODOS
        )

        # 3. Aplicar la subconsulta a la consulta principal
        stmt = stmt.where(Miembro.id.in_(subq))

    result = await db.execute(stmt)
    return result.scalars().all()

# tests/atributo_miembro/test_atributo_miembro_service.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.miembro import Miembro
from models.atributo import Atributo
from models.hogar import Hogar
from models.rol import Rol
from schemas.atributo_miembro import AtributoMiembroCreate
from services.atributo_miembro_service import (
    asignar_atributo_a_miembro,
    obtener_atributos_de_miembro,
    buscar_miembros_por_atributos,
)


@pytest_asyncio.fixture
async def setup_miembro_y_atributo(db: AsyncSession):
    """Crea un miembro y dos atributos base para los tests"""
    hogar = Hogar(id=1, nombre="Hogar Test")
    rol = Rol(id=1, nombre="Rol Test")
    miembro = Miembro(
        id=1,
        nombre_completo="Miembro Test",
        correo_electronico="test@mail.com",
        contrasena_hash="123",
        id_rol=1,
        id_hogar=1,
    )

    # --- ¡AQUÍ ESTÁ EL ARREGLO! ---
    # Asumí que 'tipo' es un string, como "texto" o "numero".
    atributo1 = Atributo(id=1, nombre="Edad", descripcion="", tipo="texto")
    atributo2 = Atributo(id=2, nombre="Color", descripcion="", tipo="texto")
    # --- FIN DEL ARREGLO ---

    db.add_all([hogar, rol, miembro, atributo1, atributo2])
    await db.flush()

    return {"miembro": miembro, "atributo1": atributo1, "atributo2": atributo2}


@pytest.mark.asyncio
async def test_asignar_atributo_a_miembro_crear(
    db: AsyncSession, setup_miembro_y_atributo
):
    """Prueba que se puede asignar un nuevo atributo a un miembro"""
    miembro_id = setup_miembro_y_atributo["miembro"].id
    atributo_id = setup_miembro_y_atributo["atributo1"].id

    datos_asignacion = AtributoMiembroCreate(
        id_miembro=miembro_id, id_atributo=atributo_id, valor="25"
    )

    resultado = await asignar_atributo_a_miembro(db, datos_asignacion)

    assert resultado is not None
    assert resultado.id_miembro == miembro_id
    assert resultado.id_atributo == atributo_id
    assert resultado.valor == "25"


@pytest.mark.asyncio
async def test_asignar_atributo_a_miembro_actualizar(
    db: AsyncSession, setup_miembro_y_atributo
):
    """Prueba que si el atributo ya existe, actualiza el valor"""
    miembro_id = setup_miembro_y_atributo["miembro"].id
    atributo_id = setup_miembro_y_atributo["atributo1"].id

    # 1. Asignamos "25"
    datos_v1 = AtributoMiembroCreate(
        id_miembro=miembro_id, id_atributo=atributo_id, valor="25"
    )
    await asignar_atributo_a_miembro(db, datos_v1)

    # 2. Asignamos "30"
    datos_v2 = AtributoMiembroCreate(
        id_miembro=miembro_id, id_atributo=atributo_id, valor="30"
    )
    resultado = await asignar_atributo_a_miembro(db, datos_v2)

    assert resultado.valor == "30"

    # Verificamos que no creó uno nuevo
    atributos_miembro = await obtener_atributos_de_miembro(db, miembro_id)
    assert len(atributos_miembro) == 1


@pytest.mark.asyncio
async def test_obtener_atributos_de_miembro(db: AsyncSession, setup_miembro_y_atributo):
    """Prueba que lista los atributos de un miembro"""
    miembro_id = setup_miembro_y_atributo["miembro"].id

    datos1 = AtributoMiembroCreate(
        id_miembro=miembro_id,
        id_atributo=setup_miembro_y_atributo["atributo1"].id,
        valor="Azul",
    )
    datos2 = AtributoMiembroCreate(
        id_miembro=miembro_id,
        id_atributo=setup_miembro_y_atributo["atributo2"].id,
        valor="Rojo",
    )

    await asignar_atributo_a_miembro(db, datos1)
    await asignar_atributo_a_miembro(db, datos2)

    atributos_miembro = await obtener_atributos_de_miembro(db, miembro_id)

    assert len(atributos_miembro) == 2


@pytest.mark.asyncio
async def test_buscar_miembros_por_atributos(
    db: AsyncSession, setup_miembro_y_atributo
):
    """Prueba la lógica de búsqueda por atributos"""
    miembro1_id = setup_miembro_y_atributo["miembro"].id
    atributo_edad_id = setup_miembro_y_atributo["atributo1"].id  # "Edad"
    atributo_color_id = setup_miembro_y_atributo["atributo2"].id  # "Color"

    # Miembro 2
    miembro2 = Miembro(
        id=2,
        nombre_completo="Miembro 2",
        correo_electronico="test2@mail.com",
        contrasena_hash="123",
        id_rol=1,
        id_hogar=1,
    )
    db.add(miembro2)
    await db.flush()

    # Asignar atributos
    # Miembro 1: Edad=30, Color=Azul
    await asignar_atributo_a_miembro(
        db,
        AtributoMiembroCreate(
            id_miembro=miembro1_id, id_atributo=atributo_edad_id, valor="30"
        ),
    )
    await asignar_atributo_a_miembro(
        db,
        AtributoMiembroCreate(
            id_miembro=miembro1_id, id_atributo=atributo_color_id, valor="Azul"
        ),
    )

    # Miembro 2: Edad=30, Color=Rojo
    await asignar_atributo_a_miembro(
        db,
        AtributoMiembroCreate(
            id_miembro=miembro2.id, id_atributo=atributo_edad_id, valor="30"
        ),
    )
    await asignar_atributo_a_miembro(
        db,
        AtributoMiembroCreate(
            id_miembro=miembro2.id, id_atributo=atributo_color_id, valor="Rojo"
        ),
    )

    # Buscar Edad=30 -> 2 miembros
    filtros1 = {"id_hogar": 1, "atributos": {"Edad": "30"}}
    resultado1 = await buscar_miembros_por_atributos(db, filtros1)
    assert len(resultado1) == 2

    # Buscar Edad=30 Y Color=Azul -> 1 miembro
    filtros2 = {"id_hogar": 1, "atributos": {"Edad": "30", "Color": "Azul"}}
    resultado2 = await buscar_miembros_por_atributos(db, filtros2)
    assert len(resultado2) == 1
    assert resultado2[0].id == miembro1_id

    # Buscar Color=Rojo -> 1 miembro
    filtros3 = {"id_hogar": 1, "atributos": {"Color": "Rojo"}}
    resultado3 = await buscar_miembros_por_atributos(db, filtros3)
    assert len(resultado3) == 1
    assert resultado3[0].id == miembro2.id

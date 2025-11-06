import pytest
from services.atributo_service import (
    crear_atributo,
    obtener_atributo,
    listar_atributos_activos,
    actualizar_atributo,
    eliminar_atributo_logico,
)


@pytest.mark.asyncio
async def test_crear_y_obtener_atributo(db):
    creado = await crear_atributo(db, "Color", "Color favorito", "VARCHAR")
    assert creado.id is not None
    assert creado.nombre == "Color"

    obtenido = await obtener_atributo(db, creado.id)
    assert obtenido is not None
    assert obtenido.id == creado.id


@pytest.mark.asyncio
async def test_listar_atributos_activos(db):
    a1 = await crear_atributo(db, "Talla", "Talla de prenda", "INT")
    a2 = await crear_atributo(db, "EsActivo", "Activo?", "BOOLEAN")
    lista = await listar_atributos_activos(db)
    ids = {a.id for a in lista}
    assert a1.id in ids and a2.id in ids


@pytest.mark.asyncio
async def test_actualizar_atributo(db):
    creado = await crear_atributo(db, "Peso", "Peso en kg", "INT")
    actualizado = await actualizar_atributo(db, creado.id, {"descripcion": "Peso (kg)"})
    assert actualizado is not None
    assert actualizado.descripcion == "Peso (kg)"


@pytest.mark.asyncio
async def test_eliminar_atributo_logico(db):
    creado = await crear_atributo(db, "Altura", "Altura en cm", "INT")
    ok = await eliminar_atributo_logico(db, creado.id)
    assert ok is True
    # Ya no debe aparecer en activos
    activos = await listar_atributos_activos(db)
    assert all(a.id != creado.id for a in activos)



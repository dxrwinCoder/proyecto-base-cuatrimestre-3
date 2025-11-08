# tests/test_hogar_service.py
import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.hogar import HogarCreate, HogarUpdate
from services.hogar_service import (
    crear_hogar,
    obtener_hogar,
    listar_hogares_activos,
    actualizar_hogar,
    eliminar_hogar_logico,
)


@pytest.mark.asyncio
async def test_crear_hogar(db: AsyncSession):
    """Prueba que se puede crear un hogar con el schema"""
    nombre_hogar = f"Hogar {uuid.uuid4().hex[:6]}"
    datos_hogar = HogarCreate(nombre=nombre_hogar)

    hogar_creado = await crear_hogar(db, datos_hogar)

    assert hogar_creado is not None
    assert hogar_creado.nombre == nombre_hogar
    assert hogar_creado.estado is True


@pytest.mark.asyncio
async def test_crear_hogar_duplicado(db: AsyncSession):
    """Prueba que el servicio evita hogares duplicados"""
    nombre_hogar = f"HogarDuplicado {uuid.uuid4().hex[:6]}"
    await crear_hogar(db, HogarCreate(nombre=nombre_hogar))

    with pytest.raises(ValueError, match="El nombre del hogar ya existe"):
        await crear_hogar(db, HogarCreate(nombre=nombre_hogar))


@pytest.mark.asyncio
async def test_listar_hogares_activos(db: AsyncSession):
    """Prueba que lista solo hogares activos"""
    await crear_hogar(db, HogarCreate(nombre="Hogar Activo 1"))
    hogar_inactivo = await crear_hogar(db, HogarCreate(nombre="Hogar Inactivo"))

    # Borrado lógico
    await eliminar_hogar_logico(db, hogar_inactivo.id)

    hogares = await listar_hogares_activos(db)

    assert len(hogares) == 1
    assert hogares[0].nombre == "Hogar Activo 1"


@pytest.mark.asyncio
async def test_actualizar_hogar(db: AsyncSession):
    """Prueba que se puede actualizar el nombre de un hogar"""
    hogar_creado = await crear_hogar(db, HogarCreate(nombre="Hogar Original"))
    datos_update = HogarUpdate(nombre="Hogar Actualizado")

    hogar_actualizado = await actualizar_hogar(db, hogar_creado.id, datos_update)

    assert hogar_actualizado is not None
    assert hogar_actualizado.nombre == "Hogar Actualizado"


@pytest.mark.asyncio
async def test_eliminar_hogar_logico(db: AsyncSession):
    """Prueba que el borrado lógico funciona"""
    hogar_creado = await crear_hogar(db, HogarCreate(nombre="Hogar a Borrar"))
    assert hogar_creado.estado is True

    resultado = await eliminar_hogar_logico(db, hogar_creado.id)
    assert resultado is True

    hogar_borrado = await obtener_hogar(db, hogar_creado.id)
    assert hogar_borrado.estado is False

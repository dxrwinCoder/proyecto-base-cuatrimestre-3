# tests/test_rol_service.py
import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.rol import RolCreate
from services.rol_service import crear_rol, obtener_rol


@pytest.mark.asyncio
async def test_crear_rol_exitoso(db: AsyncSession):
    """Prueba que se puede crear un rol nuevo"""
    datos_rol = RolCreate(
        nombre=f"Test Rol {uuid.uuid4().hex[:6]}", descripcion="Un rol de prueba"
    )

    # Probamos el servicio con el schema, como lo arreglamos
    rol_creado = await crear_rol(db, datos_rol)

    assert rol_creado is not None
    assert rol_creado.id is not None
    assert rol_creado.nombre == datos_rol.nombre


@pytest.mark.asyncio
async def test_crear_rol_duplicado(db: AsyncSession):
    """Prueba que el servicio lanza error si el nombre del rol ya existe"""
    nombre_rol = f"RolDuplicado {uuid.uuid4().hex[:6]}"
    datos_rol_1 = RolCreate(nombre=nombre_rol, descripcion="Rol 1")
    datos_rol_2 = RolCreate(nombre=nombre_rol, descripcion="Rol 2")

    # Creamos el primero
    await crear_rol(db, datos_rol_1)

    # El segundo debe fallar con el ValueError que pusimos
    with pytest.raises(ValueError, match="El nombre del rol ya existe"):
        await crear_rol(db, datos_rol_2)


@pytest.mark.asyncio
async def test_obtener_rol_existente(db: AsyncSession):
    """Prueba que podemos obtener un rol por su ID"""
    datos_rol = RolCreate(
        nombre=f"RolBuscable {uuid.uuid4().hex[:6]}", descripcion="Rol para buscar"
    )
    rol_creado = await crear_rol(db, datos_rol)

    rol_encontrado = await obtener_rol(db, rol_creado.id)

    assert rol_encontrado is not None
    assert rol_encontrado.id == rol_creado.id


@pytest.mark.asyncio
async def test_obtener_rol_no_existente(db: AsyncSession):
    """Prueba que obtener un rol inexistente devuelve None"""
    rol_encontrado = await obtener_rol(db, 9999)
    assert rol_encontrado is None

import pytest
import pytest_asyncio
import uuid
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from services.miembro_service import (
    crear_miembro,
    obtener_miembro,
    listar_miembros_activos_por_hogar,
    actualizar_miembro,
    desactivar_miembro,
    obtener_todos_los_miembros,
    contar_miembros_por_hogar,
    obtener_miembros_por_rol,
)
from utils.security import obtener_hash_contrasena


@pytest_asyncio.fixture
async def setup_datos_miembro(db):
    """Fixture para crear datos base para tests de miembros"""
    from sqlalchemy import select

    # Crear o obtener rol 1
    rol1_result = await db.execute(select(Rol).where(Rol.id == 1))
    rol1 = rol1_result.scalar_one_or_none()
    if not rol1:
        rol1 = Rol(id=1, nombre="Administrador", descripcion="Rol admin", estado=True)
        db.add(rol1)

    # Crear rol 2
    rol2_result = await db.execute(select(Rol).where(Rol.id == 2))
    rol2 = rol2_result.scalar_one_or_none()
    if not rol2:
        rol2 = Rol(id=2, nombre="Usuario", descripcion="Rol usuario", estado=True)
        db.add(rol2)

    # Crear o obtener hogar 1
    hogar1_result = await db.execute(select(Hogar).where(Hogar.id == 1))
    hogar1 = hogar1_result.scalar_one_or_none()
    if not hogar1:
        hogar1 = Hogar(id=1, nombre="Hogar 1", estado=True)
        db.add(hogar1)

    # Crear hogar 2
    hogar2_result = await db.execute(select(Hogar).where(Hogar.id == 2))
    hogar2 = hogar2_result.scalar_one_or_none()
    if not hogar2:
        hogar2 = Hogar(id=2, nombre="Hogar 2", estado=True)
        db.add(hogar2)

    # await db.commit()
    await db.flush()


@pytest.mark.asyncio
async def test_crear_miembro(db, setup_datos_miembro):
    """Test para crear un nuevo miembro"""
    correo = f"nuevo_{uuid.uuid4().hex[:8]}@example.com"
    data = {
        "nombre_completo": "Nuevo Miembro",
        "correo_electronico": correo,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }

    miembro = await crear_miembro(db, data)

    assert miembro is not None
    assert miembro.id is not None
    assert miembro.nombre_completo == "Nuevo Miembro"
    assert miembro.correo_electronico == correo
    assert miembro.id_rol == 1
    assert miembro.id_hogar == 1
    assert miembro.estado is True


@pytest.mark.asyncio
async def test_crear_miembro_correo_duplicado(db, setup_datos_miembro):
    """Test para intentar crear miembro con correo duplicado"""
    correo = f"duplicado_{uuid.uuid4().hex[:8]}@example.com"
    data1 = {
        "nombre_completo": "Miembro 1",
        "correo_electronico": correo,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }
    await crear_miembro(db, data1)

    data2 = {
        "nombre_completo": "Miembro 2",
        "correo_electronico": correo,  # Mismo correo
        "contrasena": "password456",
        "id_rol": 1,
        "id_hogar": 1,
    }

    with pytest.raises(ValueError, match="ya está registrado"):
        await crear_miembro(db, data2)


@pytest.mark.asyncio
async def test_obtener_miembro_existente(db, setup_datos_miembro):
    """Test para obtener un miembro existente"""
    correo = f"test_{uuid.uuid4().hex[:8]}@example.com"
    # Crear miembro
    data = {
        "nombre_completo": "Miembro Test",
        "correo_electronico": correo,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }
    miembro_creado = await crear_miembro(db, data)

    # Obtener miembro
    miembro = await obtener_miembro(db, miembro_creado.id)

    assert miembro is not None
    assert miembro.id == miembro_creado.id
    assert miembro.nombre_completo == "Miembro Test"
    assert miembro.correo_electronico == correo


@pytest.mark.asyncio
async def test_obtener_miembro_no_existe(db, setup_datos_miembro):
    """Test para obtener un miembro que no existe"""
    miembro = await obtener_miembro(db, 999)

    assert miembro is None


@pytest.mark.asyncio
async def test_listar_miembros_activos_por_hogar(db, setup_datos_miembro):
    """Test para listar miembros activos de un hogar"""
    # Crear miembros en hogar 1
    correo1 = f"miembro1_{uuid.uuid4().hex[:8]}@example.com"
    correo2 = f"miembro2_{uuid.uuid4().hex[:8]}@example.com"
    correo3 = f"miembro3_{uuid.uuid4().hex[:8]}@example.com"

    data1 = {
        "nombre_completo": "Miembro 1",
        "correo_electronico": correo1,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }
    data2 = {
        "nombre_completo": "Miembro 2",
        "correo_electronico": correo2,
        "contrasena": "password123",
        "id_rol": 2,
        "id_hogar": 1,
    }
    # Miembro en otro hogar
    data3 = {
        "nombre_completo": "Miembro 3",
        "correo_electronico": correo3,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 2,
    }

    await crear_miembro(db, data1)
    await crear_miembro(db, data2)
    await crear_miembro(db, data3)

    # Listar miembros del hogar 1
    miembros = await listar_miembros_activos_por_hogar(db, 1)

    assert len(miembros) == 2
    assert all(m.id_hogar == 1 for m in miembros)
    assert all(m.estado is True for m in miembros)


@pytest.mark.asyncio
async def test_actualizar_miembro(db, setup_datos_miembro):
    """Test para actualizar un miembro"""
    correo = f"original_{uuid.uuid4().hex[:8]}@example.com"
    # Crear miembro
    data = {
        "nombre_completo": "Miembro Original",
        "correo_electronico": correo,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }
    miembro_creado = await crear_miembro(db, data)

    # Actualizar miembro
    update_data = {
        "nombre_completo": "Miembro Actualizado",
        "id_rol": 2,
    }

    miembro_actualizado = await actualizar_miembro(db, miembro_creado.id, update_data)

    assert miembro_actualizado is not None
    assert miembro_actualizado.nombre_completo == "Miembro Actualizado"
    assert miembro_actualizado.id_rol == 2
    assert miembro_actualizado.correo_electronico == correo  # No cambió


@pytest.mark.asyncio
async def test_actualizar_miembro_no_existe(db, setup_datos_miembro):
    """Test para actualizar un miembro que no existe"""
    update_data = {"nombre_completo": "Nuevo Nombre"}

    resultado = await actualizar_miembro(db, 999, update_data)

    assert resultado is None


@pytest.mark.asyncio
async def test_actualizar_miembro_correo_duplicado(db, setup_datos_miembro):
    """Test para actualizar miembro con correo ya existente"""
    correo1 = f"miembro1_{uuid.uuid4().hex[:8]}@example.com"
    correo2 = f"miembro2_{uuid.uuid4().hex[:8]}@example.com"

    # Crear dos miembros
    data1 = {
        "nombre_completo": "Miembro 1",
        "correo_electronico": correo1,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }
    data2 = {
        "nombre_completo": "Miembro 2",
        "correo_electronico": correo2,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }
    miembro1 = await crear_miembro(db, data1)
    await crear_miembro(db, data2)

    # Intentar actualizar miembro1 con correo de miembro2
    update_data = {"correo_electronico": correo2}

    with pytest.raises(ValueError, match="ya está registrado"):
        await actualizar_miembro(db, miembro1.id, update_data)


@pytest.mark.asyncio
async def test_desactivar_miembro(db, setup_datos_miembro):
    """Test para desactivar un miembro"""
    correo = f"test_{uuid.uuid4().hex[:8]}@example.com"
    # Crear miembro
    data = {
        "nombre_completo": "Miembro Test",
        "correo_electronico": correo,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }
    miembro_creado = await crear_miembro(db, data)
    assert miembro_creado.estado is True

    # Desactivar miembro
    resultado = await desactivar_miembro(db, miembro_creado.id)

    assert resultado is True

    # Verificar que está desactivado
    miembro = await obtener_miembro(db, miembro_creado.id)
    assert miembro.estado is False


@pytest.mark.asyncio
async def test_desactivar_miembro_no_existe(db, setup_datos_miembro):
    """Test para desactivar un miembro que no existe"""
    resultado = await desactivar_miembro(db, 999)

    assert resultado is False


@pytest.mark.asyncio
async def test_obtener_todos_los_miembros(db, setup_datos_miembro):
    """Test para obtener todos los miembros"""
    # Crear varios miembros
    for i in range(3):
        correo = f"miembro{i+1}_{uuid.uuid4().hex[:8]}@example.com"
        data = {
            "nombre_completo": f"Miembro {i+1}",
            "correo_electronico": correo,
            "contrasena": "password123",
            "id_rol": 1,
            "id_hogar": 1,
        }
        await crear_miembro(db, data)

    miembros = await obtener_todos_los_miembros(db)

    assert len(miembros) >= 3


@pytest.mark.asyncio
async def test_contar_miembros_por_hogar(db, setup_datos_miembro):
    """Test para contar miembros activos por hogar"""
    # Crear miembros en hogar 1
    for i in range(2):
        correo = f"hogar1_{i+1}_{uuid.uuid4().hex[:8]}@example.com"
        data = {
            "nombre_completo": f"Miembro Hogar1 {i+1}",
            "correo_electronico": correo,
            "contrasena": "password123",
            "id_rol": 1,
            "id_hogar": 1,
        }
        await crear_miembro(db, data)

    correo = f"hogar2_{uuid.uuid4().hex[:8]}@example.com"
    # Crear miembro en hogar 2
    data = {
        "nombre_completo": "Miembro Hogar2",
        "correo_electronico": correo,
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 2,
    }
    await crear_miembro(db, data)

    # Contar miembros del hogar 1
    cantidad = await contar_miembros_por_hogar(db, 1)

    assert cantidad == 2


@pytest.mark.asyncio
async def test_obtener_miembros_por_rol(db, setup_datos_miembro):
    """Test para obtener miembros por rol"""
    correo1 = f"admin1_{uuid.uuid4().hex[:8]}@example.com"
    correo2 = f"admin2_{uuid.uuid4().hex[:8]}@example.com"
    correo3 = f"usuario1_{uuid.uuid4().hex[:8]}@example.com"

    # Crear miembros con diferentes roles
    data1 = {
        "nombre_completo": "Admin 1",
        "correo_electronico": correo1,
        "contrasena": "password123",
        "id_rol": 1,  # Administrador
        "id_hogar": 1,
    }
    data2 = {
        "nombre_completo": "Admin 2",
        "correo_electronico": correo2,
        "contrasena": "password123",
        "id_rol": 1,  # Administrador
        "id_hogar": 1,
    }
    data3 = {
        "nombre_completo": "Usuario 1",
        "correo_electronico": correo3,
        "contrasena": "password123",
        "id_rol": 2,  # Usuario
        "id_hogar": 1,
    }

    await crear_miembro(db, data1)
    await crear_miembro(db, data2)
    await crear_miembro(db, data3)

    # Obtener miembros con rol 1 (Administrador)
    miembros = await obtener_miembros_por_rol(db, 1)

    assert len(miembros) == 2
    assert all(m.id_rol == 1 for m in miembros)

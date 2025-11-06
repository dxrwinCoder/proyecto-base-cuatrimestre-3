import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.modulo import Modulo
from models.permiso import Permiso
from utils.security import crear_token_acceso


@pytest_asyncio.fixture
async def client(db):
    # Sobrescribir la dependencia get_db para usar la base de datos de test
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Limpiar el override después del test
    app.dependency_overrides.clear()


def crear_token_test():
    return crear_token_acceso({"sub": "1", "id_hogar": 1})


@pytest_asyncio.fixture
async def setup_miembro(db, setup_rol_hogar):
    from sqlalchemy import select
    
    # Crear módulo de prueba
    modulo_result = await db.execute(select(Modulo).where(Modulo.id == 1))
    modulo = modulo_result.scalar_one_or_none()
    if not modulo:
        modulo = Modulo(
            id=1,
            nombre="Tareas",
            descripcion="Módulo de tareas",
            estado=True,
        )
        db.add(modulo)

    # Crear permiso para crear tareas
    permiso_result = await db.execute(
        select(Permiso).where(Permiso.id_rol == 1, Permiso.id_modulo == 1)
    )
    permiso = permiso_result.scalar_one_or_none()
    if not permiso:
        permiso = Permiso(
            id_rol=1,
            id_modulo=1,
            puede_crear=True,
            puede_leer=True,
            puede_actualizar=True,
            puede_eliminar=True,
            estado=True,
        )
        db.add(permiso)

    # Crear miembro de prueba
    miembro_result = await db.execute(select(Miembro).where(Miembro.id == 1))
    miembro = miembro_result.scalar_one_or_none()
    if not miembro:
        miembro = Miembro(
            id=1,
            nombre_completo="Test User",
            correo_electronico="test@example.com",
            contrasena_hash="fake_hash",
            id_rol=1,
            id_hogar=1,
            estado=True,
        )
        db.add(miembro)
    
    await db.commit()
    await db.refresh(miembro)
    yield miembro


@pytest.mark.asyncio
async def test_crear_tarea_con_autenticacion(client, setup_miembro):
    token = crear_token_test()
    headers = {"Authorization": f"Bearer {token}"}
    tarea_data = {
        "titulo": "Lavar platos",
        "categoria": "cocina",
        "asignado_a": 1,
        "id_hogar": 1,
    }
    response = await client.post("/tareas/", json=tarea_data, headers=headers)
    assert response.status_code == 200

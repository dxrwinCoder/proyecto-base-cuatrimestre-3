import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from utils.security import obtener_hash_contrasena


@pytest_asyncio.fixture
async def client(db):
    """Fixture para crear cliente HTTP con BD de test"""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_datos_auth(db, setup_rol_hogar):
    """Fixture para crear datos necesarios para tests de autenticación"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Verificar si ya existe un miembro con este correo
    correo = "test_auth@example.com"
    miembro_existente = await db.execute(
        select(Miembro).where(Miembro.correo_electronico == correo)
    )
    miembro = miembro_existente.scalar_one_or_none()

    if not miembro:
        # Crear miembro de prueba
        contrasena_plana = "password123"
        contrasena_hash = obtener_hash_contrasena(contrasena_plana)

        miembro = Miembro(
            nombre_completo="Test User",
            correo_electronico=correo,
            contrasena_hash=contrasena_hash,
            id_rol=1,
            id_hogar=1,
            estado=True,
        )
        db.add(miembro)
        # await db.commit()
        await db.flush()

        if miembro:
            await db.refresh(miembro)
    # Recargar miembro con rol usando eager loading
    result = await db.execute(
        select(Miembro)
        .options(selectinload(Miembro.rol))
        .where(Miembro.correo_electronico == correo)
    )
    miembro = result.scalar_one()

    yield {"miembro": miembro, "contrasena": "password123"}


@pytest.mark.asyncio
async def test_registro_miembro_exitoso(client, setup_datos_auth):
    """Test para registrar un nuevo miembro exitosamente"""
    datos_registro = {
        "nombre_completo": "Nuevo Usuario",
        "correo_electronico": "nuevo@example.com",
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }

    response = await client.post("/auth/registro", json=datos_registro)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["id_miembro"] is not None
    assert data["id_hogar"] == 1
    assert data["access_token"] is not None


@pytest.mark.asyncio
async def test_registro_miembro_correo_duplicado(client, setup_datos_auth):
    """Test para intentar registrar un miembro con correo ya existente"""
    datos_registro = {
        "nombre_completo": "Otro Usuario",
        "correo_electronico": setup_datos_auth[
            "miembro"
        ].correo_electronico,  # Ya existe
        "contrasena": "password123",
        "id_rol": 1,
        "id_hogar": 1,
    }

    response = await client.post("/auth/registro", json=datos_registro)

    assert response.status_code == 400
    data = response.json()
    assert "ya se encuentra registrado" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_exitoso(client, setup_datos_auth):
    """Test para login exitoso con credenciales correctas"""
    datos_login = {
        "correo_electronico": setup_datos_auth["miembro"].correo_electronico,
        "contrasena": setup_datos_auth["contrasena"],
    }

    response = await client.post("/auth/login", json=datos_login)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["id_miembro"] == 1
    assert data["id_hogar"] == 1
    assert data["access_token"] is not None


@pytest.mark.asyncio
async def test_login_credenciales_incorrectas(client, setup_datos_auth):
    """Test para login con contraseña incorrecta"""
    datos_login = {
        "correo_electronico": setup_datos_auth["miembro"].correo_electronico,
        "contrasena": "contraseña_incorrecta",
    }

    response = await client.post("/auth/login", json=datos_login)

    assert response.status_code == 401
    data = response.json()
    assert "incorrectas" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_usuario_no_existe(client, setup_datos_auth):
    """Test para login con usuario que no existe"""
    datos_login = {
        "correo_electronico": "noexiste@example.com",
        "contrasena": "password123",
    }

    response = await client.post("/auth/login", json=datos_login)

    assert response.status_code == 401
    data = response.json()
    assert "incorrectas" in data["detail"].lower()


@pytest.mark.asyncio
async def test_registro_validacion_contrasena_corta(client, setup_datos_auth):
    """Test para validar que la contraseña debe tener al menos 8 caracteres"""
    datos_registro = {
        "nombre_completo": "Usuario Test",
        "correo_electronico": "test2@example.com",
        "contrasena": "12345",  # Menos de 8 caracteres
        "id_rol": 1,
        "id_hogar": 1,
    }

    response = await client.post("/auth/registro", json=datos_registro)

    # FastAPI debería validar el schema y retornar 422
    assert response.status_code == 422

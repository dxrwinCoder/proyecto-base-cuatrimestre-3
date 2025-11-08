# tests/mensaje/test_mensaje_routes.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from models.mensaje import Mensaje  # <-- ¡Importar Mensaje!
from utils.security import crear_token_acceso, obtener_hash_contrasena


# --- Fixtures de Cliente y Token (¡Necesarias!) ---
@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """Fixture para crear cliente HTTP con BD de test"""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def crear_token_test(miembro_id=1, id_hogar=1, id_rol=1):
    """Función helper para crear token de prueba"""
    # El 'sub' (subject) debe ser el 'miembro_id' como string
    return crear_token_acceso(
        {"sub": str(miembro_id), "id_hogar": id_hogar, "id_rol": id_rol}
    )


@pytest_asyncio.fixture
async def setup_miembros_y_mensajes(db: AsyncSession, setup_rol_hogar):
    """Crea 2 miembros en 2 hogares y mensajes en el hogar 1"""

    # Hogar 1 ya existe (de setup_rol_hogar)
    # Rol 1 ya existe (de setup_rol_hogar)

    # Hogar 2
    hogar2 = Hogar(id=2, nombre="Hogar 2")
    db.add(hogar2)

    # Miembro 1 (Hogar 1)
    miembro1 = Miembro(
        id=1,
        nombre_completo="Miembro 1 Hogar 1",
        correo_electronico="m1@mail.com",
        contrasena_hash="123",
        id_rol=1,
        id_hogar=1,
    )
    # Miembro 2 (Hogar 2)
    miembro2 = Miembro(
        id=2,
        nombre_completo="Miembro 2 Hogar 2",
        correo_electronico="m2@mail.com",
        contrasena_hash="123",
        id_rol=1,
        id_hogar=2,
    )
    db.add_all([miembro1, miembro2])
    await db.flush()

    # Mensajes
    msg1 = Mensaje(id_hogar=1, id_remitente=miembro1.id, contenido="Hola Hogar 1")
    msg2 = Mensaje(id_hogar=1, id_remitente=miembro1.id, contenido="Segundo mensaje H1")
    msg3_h2 = Mensaje(
        id_hogar=2, id_remitente=miembro2.id, contenido="Mensaje del Hogar 2"
    )

    db.add_all([msg1, msg2, msg3_h2])
    await db.flush()

    return {"miembro1": miembro1, "miembro2": miembro2}


@pytest.mark.asyncio
async def test_listar_mensajes_hogar_exitoso(
    client: AsyncClient, setup_miembros_y_mensajes
):
    """Prueba que un miembro puede ver los mensajes de SU hogar"""
    miembro1 = setup_miembros_y_mensajes["miembro1"]
    token = crear_token_test(
        miembro_id=miembro1.id, id_hogar=miembro1.id_hogar, id_rol=miembro1.id_rol
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/mensajes/hogar/{miembro1.id_hogar}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Corrección del assert (Parche anterior que faltaba)
    assert data[0]["remitente"]["id"] == miembro1.id
    assert data[0]["remitente"]["nombre_completo"] == "Miembro 1 Hogar 1"
    # --- FIN DEL PARCHE ---


@pytest.mark.asyncio
async def test_listar_mensajes_hogar_ajeno_falla(
    client: AsyncClient, setup_miembros_y_mensajes
):
    """Prueba que un miembro NO puede ver mensajes de OTRO hogar (403)"""
    miembro1 = setup_miembros_y_mensajes["miembro1"]  # Pertenece al hogar 1
    miembro2 = setup_miembros_y_mensajes["miembro2"]  # Pertenece al hogar 2

    token_miembro1 = crear_token_test(
        miembro_id=miembro1.id, id_hogar=miembro1.id_hogar, id_rol=miembro1.id_rol
    )
    headers = {"Authorization": f"Bearer {token_miembro1}"}

    # El miembro 1 intenta ver los mensajes del hogar 2
    response = await client.get(f"/mensajes/hogar/{miembro2.id_hogar}", headers=headers)

    assert response.status_code == 403
    assert "No perteneces a este hogar" in response.json()["detail"]


@pytest.mark.asyncio
async def test_listar_mensajes_sin_token(client: AsyncClient):
    """Prueba que la ruta de mensajes está protegida (401)"""
    response = await client.get("/mensajes/hogar/1")
    assert response.status_code == 401

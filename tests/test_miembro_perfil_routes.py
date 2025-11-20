import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from utils.security import crear_token_acceso, obtener_hash_contrasena
from schemas.miembro import MiembroUpdate


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_miembro(db):
    rol = Rol(id=4, nombre="MiembroPerfil")
    hogar = Hogar(id=30, nombre="Hogar Perfil")
    miembro = Miembro(
        id=80,
        nombre_completo="Perfil User",
        correo_electronico="perfil@user.com",
        contrasena_hash=obtener_hash_contrasena("pass12345"),
        id_rol=rol.id,
        id_hogar=hogar.id,
        estado=True,
    )
    db.add_all([rol, hogar, miembro])
    await db.flush()
    return miembro


def token(miembro: Miembro):
    return crear_token_acceso(
        {"sub": str(miembro.id), "id_hogar": miembro.id_hogar, "id_rol": miembro.id_rol}
    )


@pytest.mark.asyncio
async def test_ver_perfil(client, setup_miembro):
    headers = {"Authorization": f"Bearer {token(setup_miembro)}"}
    resp = await client.get("/miembros/perfil", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == setup_miembro.id


@pytest.mark.asyncio
async def test_actualizar_perfil(client, setup_miembro):
    headers = {"Authorization": f"Bearer {token(setup_miembro)}"}
    payload = {"nombre_completo": "Nuevo Nombre"}
    resp = await client.put("/miembros/perfil", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["nombre_completo"] == "Nuevo Nombre"

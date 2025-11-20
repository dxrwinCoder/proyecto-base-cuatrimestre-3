import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from models.notificacion import Notificacion
from utils.security import crear_token_acceso, obtener_hash_contrasena
from datetime import datetime


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_notificaciones(db):
    rol = Rol(id=3, nombre="MiembroNotif")
    hogar = Hogar(id=20, nombre="Hogar Notifs")
    miembro = Miembro(
        id=70,
        nombre_completo="Notif User",
        correo_electronico="notif@user.com",
        contrasena_hash=obtener_hash_contrasena("pass12345"),
        id_rol=rol.id,
        id_hogar=hogar.id,
        estado=True,
    )
    notif = Notificacion(
        id_miembro_destino=miembro.id,
        id_miembro_origen=None,
        tipo="prueba",
        mensaje="Hola",
        estado=1,
        id_tarea=None,
        id_evento=None,
        fecha_creacion=datetime.now(),
    )
    db.add_all([rol, hogar, miembro, notif])
    await db.flush()
    return miembro


def token(miembro: Miembro):
    return crear_token_acceso(
        {"sub": str(miembro.id), "id_hogar": miembro.id_hogar, "id_rol": miembro.id_rol}
    )


@pytest.mark.asyncio
async def test_listar_notificaciones_mias(client, setup_notificaciones):
    miembro = setup_notificaciones
    headers = {"Authorization": f"Bearer {token(miembro)}"}
    resp = await client.get("/notificaciones/mias", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

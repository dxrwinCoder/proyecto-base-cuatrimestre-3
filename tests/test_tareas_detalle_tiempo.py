import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta

from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from models.tarea import Tarea
from utils.security import crear_token_acceso, obtener_hash_contrasena


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_tarea_miembro(db):
    rol = Rol(id=5, nombre="MiembroTarea")
    hogar = Hogar(id=40, nombre="Hogar Tareas")
    miembro = Miembro(
        id=90,
        nombre_completo="Tarea User",
        correo_electronico="tarea@user.com",
        contrasena_hash=obtener_hash_contrasena("pass12345"),
        id_rol=rol.id,
        id_hogar=hogar.id,
        estado=True,
    )
    tarea = Tarea(
        titulo="Tarea tiempo",
        descripcion="Test",
        categoria="cocina",
        repeticion="ninguna",
        asignado_a=miembro.id,
        id_hogar=hogar.id,
        estado_actual="pendiente",
        fecha_asignacion=datetime.now() - timedelta(days=1),
        fecha_limite=datetime.now().date() + timedelta(days=1),
    )
    db.add_all([rol, hogar, miembro, tarea])
    await db.flush()
    return miembro


def token(miembro: Miembro):
    return crear_token_acceso(
        {"sub": str(miembro.id), "id_hogar": miembro.id_hogar, "id_rol": miembro.id_rol}
    )


@pytest.mark.asyncio
async def test_tareas_detalle_tiempo(client, setup_tarea_miembro):
    headers = {"Authorization": f"Bearer {token(setup_tarea_miembro)}"}
    resp = await client.get("/tareas/mias/detalle-tiempo", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert "tiempo_transcurrido_min" in data[0]

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta

from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from models.evento import Evento
from models.tarea import Tarea
from utils.security import crear_token_acceso, obtener_hash_contrasena


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_evento_con_tarea(db):
    # Rol y hogar
    rol = Rol(id=2, nombre="Miembro")
    hogar = Hogar(id=10, nombre="Hogar Eventos")
    db.add_all([rol, hogar])

    miembro = Miembro(
        id=50,
        nombre_completo="Usuario Eventos",
        correo_electronico="user@events.com",
        contrasena_hash=obtener_hash_contrasena("pass12345"),
        id_rol=rol.id,
        id_hogar=hogar.id,
        estado=True,
    )
    db.add(miembro)

    evento = Evento(
        id=100,
        titulo="Evento Semana",
        descripcion="Test",
        fecha_hora=datetime.now(),
        duracion_min=60,
        id_hogar=hogar.id,
        creado_por=miembro.id,
        estado=True,
    )
    db.add(evento)

    tarea = Tarea(
        titulo="Tarea evento",
        descripcion="Test",
        categoria="cocina",
        repeticion="ninguna",
        asignado_a=miembro.id,
        id_hogar=hogar.id,
        id_evento=evento.id,
        estado_actual="pendiente",
        fecha_asignacion=datetime.now() - timedelta(days=1),
    )
    db.add(tarea)
    await db.flush()
    return {"miembro": miembro}


def token_para(miembro: Miembro):
    return crear_token_acceso(
        {"sub": str(miembro.id), "id_hogar": miembro.id_hogar, "id_rol": miembro.id_rol}
    )


@pytest.mark.asyncio
async def test_eventos_mis_datasets(client, setup_evento_con_tarea):
    miembro = setup_evento_con_tarea["miembro"]
    headers = {"Authorization": f"Bearer {token_para(miembro)}"}

    resp_mes = await client.get("/eventos/mis-eventos/mes-actual", headers=headers)
    assert resp_mes.status_code == 200

    resp_semana = await client.get(
        "/eventos/mis-eventos/semana-actual", headers=headers
    )
    assert resp_semana.status_code == 200

    resp_general = await client.get("/eventos/mis-eventos", headers=headers)
    assert resp_general.status_code == 200

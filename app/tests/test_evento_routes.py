import pytest
import pytest_asyncio
from datetime import datetime, UTC
from httpx import AsyncClient, ASGITransport
from main import app
from db.database import get_db


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


@pytest.mark.asyncio
async def test_crear_evento(client, setup_rol_hogar):
    payload = {
        "titulo": "Cumpleaños",
        "descripcion": "Fiesta",
        "fecha_hora": datetime.now(UTC).isoformat(),
        "duracion_min": 120,
        "id_hogar": 1,
        "creado_por": 1,
    }
    resp = await client.post("/eventos/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["titulo"] == "Cumpleaños"
    assert data["id_hogar"] == 1


@pytest.mark.asyncio
async def test_listar_eventos_por_hogar(client, setup_rol_hogar):
    # Crear uno para asegurar datos
    await client.post(
        "/eventos/",
        json={
            "titulo": "Reunión",
            "descripcion": None,
            "fecha_hora": datetime.now(UTC).isoformat(),
            "duracion_min": 60,
            "id_hogar": 1,
            "creado_por": 1,
        },
    )

    resp = await client.get("/eventos/hogar/1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

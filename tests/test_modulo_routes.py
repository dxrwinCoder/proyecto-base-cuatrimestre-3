import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from db.database import get_db


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_crear_modulo(client):
    payload = {"nombre": "Tareas", "descripcion": "Gestión de tareas"}
    resp = await client.post("/modulos/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nombre"] == "Tareas"



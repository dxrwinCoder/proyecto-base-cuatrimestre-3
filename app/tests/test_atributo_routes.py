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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_crear_y_ver_atributo(client):
    payload = {"nombre": "Color", "descripcion": "Color favorito", "tipo": "VARCHAR"}
    resp = await client.post("/atributos/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nombre"] == "Color"
    attr_id = data["id"]

    resp_get = await client.get(f"/atributos/{attr_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == attr_id


@pytest.mark.asyncio
async def test_listar_atributos(client):
    # Crear uno para asegurar lista no vacía
    await client.post(
        "/atributos/", json={"nombre": "Talla", "descripcion": "Talla", "tipo": "INT"}
    )
    resp = await client.get("/atributos/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_actualizar_y_eliminar_atributo(client):
    # Crear
    create = await client.post(
        "/atributos/", json={"nombre": "Peso", "descripcion": "kg", "tipo": "INT"}
    )
    attr = create.json()
    attr_id = attr["id"]

    # Actualizar
    upd = await client.put(
        f"/atributos/{attr_id}",
        json={"nombre": "Peso", "descripcion": "Peso (kg)", "tipo": "INT"},
    )
    assert upd.status_code == 200
    assert upd.json()["descripcion"] == "Peso (kg)"

    # Eliminar (baja lógica)
    dele = await client.delete(f"/atributos/{attr_id}")
    assert dele.status_code == 200

    # Ya no visible: GET por id debe dar 404
    resp_404 = await client.get(f"/atributos/{attr_id}")
    assert resp_404.status_code == 404

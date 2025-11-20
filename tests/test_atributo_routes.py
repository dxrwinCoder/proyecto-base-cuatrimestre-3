import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.miembro import Miembro
from models.modulo import Modulo
from models.permiso import Permiso
from utils.security import crear_token_acceso, obtener_hash_contrasena
from models.rol import Rol
from models.hogar import Hogar


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
async def admin_con_permiso_atributos(db: AsyncSession):
    """
    Crea un admin con permisos completos sobre el módulo Atributos para probar las rutas.
    """
    # Rol y hogar base (alineado a conftest)
    rol = await db.get(Rol, 1) or Rol(id=1, nombre="Administrador", descripcion="Admin")
    hogar = await db.get(Hogar, 1) or Hogar(id=1, nombre="Hogar Test")
    db.add_all([rol, hogar])

    # Módulo Atributos
    modulo = (await db.execute(select(Modulo).where(Modulo.nombre == "Atributos"))).scalar_one_or_none()
    if not modulo:
        modulo = Modulo(nombre="Atributos", descripcion="Módulo de atributos")
        db.add(modulo)
        await db.flush()

    # Admin
    admin = (await db.execute(select(Miembro).where(Miembro.id == 1))).scalar_one_or_none()
    if not admin:
        admin = Miembro(
            id=1,
            nombre_completo="Admin Atributos",
            correo_electronico="admin_attr@example.com",
            contrasena_hash=obtener_hash_contrasena("admin123"),
            id_rol=rol.id,
            id_hogar=hogar.id,
            estado=True,
        )
        db.add(admin)

    # Permiso CRUD completo
    permiso = (
        await db.execute(
            select(Permiso).where(Permiso.id_rol == rol.id, Permiso.id_modulo == modulo.id)
        )
    ).scalar_one_or_none()
    if not permiso:
        permiso = Permiso(
            id_rol=rol.id,
            id_modulo=modulo.id,
            puede_crear=True,
            puede_leer=True,
            puede_actualizar=True,
            puede_eliminar=True,
        )
        db.add(permiso)

    await db.flush()
    await db.refresh(admin)
    return admin


def token_para(miembro: Miembro):
    return crear_token_acceso(
        {"sub": str(miembro.id), "id_hogar": miembro.id_hogar, "rol": "Administrador"}
    )


@pytest.mark.asyncio
async def test_crear_y_ver_atributo(client, admin_con_permiso_atributos):
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_atributos)}"}
    payload = {"nombre": "Color", "descripcion": "Color favorito", "tipo": "VARCHAR"}
    resp = await client.post("/atributos/", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Color"
    attr_id = data["id"]

    resp_get = await client.get(f"/atributos/{attr_id}", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == attr_id


@pytest.mark.asyncio
async def test_listar_atributos(client, admin_con_permiso_atributos):
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_atributos)}"}
    # Crear uno para asegurar lista no vacía
    await client.post(
        "/atributos/",
        json={"nombre": "Talla", "descripcion": "Talla", "tipo": "INT"},
        headers=headers,
    )
    resp = await client.get("/atributos/", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_actualizar_y_eliminar_atributo(client, admin_con_permiso_atributos):
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_atributos)}"}
    # Crear
    create = await client.post(
        "/atributos/",
        json={"nombre": "Peso", "descripcion": "kg", "tipo": "INT"},
        headers=headers,
    )
    attr = create.json()
    attr_id = attr["id"]

    # Actualizar
    upd = await client.put(
        f"/atributos/{attr_id}",
        json={"nombre": "Peso", "descripcion": "Peso (kg)", "tipo": "INT"},
        headers=headers,
    )
    assert upd.status_code == 200
    assert upd.json()["descripcion"] == "Peso (kg)"

    # Eliminar (baja lógica)
    dele = await client.delete(f"/atributos/{attr_id}", headers=headers)
    assert dele.status_code == 200

    # Ya no visible: GET por id debe dar 404
    resp_404 = await client.get(f"/atributos/{attr_id}", headers=headers)
    assert resp_404.status_code == 404

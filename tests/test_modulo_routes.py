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
from models.rol import Rol
from models.hogar import Hogar
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
async def admin_con_permiso_modulos(db: AsyncSession):
    rol = await db.get(Rol, 1) or Rol(id=1, nombre="Administrador")
    hogar = await db.get(Hogar, 1) or Hogar(id=1, nombre="Hogar Test")
    db.add_all([rol, hogar])

    modulo_modulos = (await db.execute(select(Modulo).where(Modulo.nombre == "Modulos"))).scalar_one_or_none()
    if not modulo_modulos:
        modulo_modulos = Modulo(nombre="Modulos", descripcion="Módulo de gestión de módulos")
        db.add(modulo_modulos)
        await db.flush()

    admin = (await db.execute(select(Miembro).where(Miembro.id == 1))).scalar_one_or_none()
    if not admin:
        admin = Miembro(
            id=1,
            nombre_completo="Admin Modulos",
            correo_electronico="admin_mod@example.com",
            contrasena_hash=obtener_hash_contrasena("admin123"),
            id_rol=rol.id,
            id_hogar=hogar.id,
            estado=True,
        )
        db.add(admin)

    permiso = (
        await db.execute(
            select(Permiso).where(Permiso.id_rol == rol.id, Permiso.id_modulo == modulo_modulos.id)
        )
    ).scalar_one_or_none()
    if not permiso:
        permiso = Permiso(
            id_rol=rol.id,
            id_modulo=modulo_modulos.id,
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
async def test_crear_modulo(client, admin_con_permiso_modulos):
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_modulos)}"}
    payload = {"nombre": "Tareas", "descripcion": "Gestión de tareas"}
    resp = await client.post("/modulos/", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Tareas"



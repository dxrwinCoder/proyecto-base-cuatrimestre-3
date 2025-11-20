import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_con_permiso_eventos(db: AsyncSession):
    rol = await db.get(Rol, 1) or Rol(id=1, nombre="Administrador")
    hogar = await db.get(Hogar, 1) or Hogar(id=1, nombre="Hogar Test")
    db.add_all([rol, hogar])

    modulo_eventos = (await db.execute(select(Modulo).where(Modulo.nombre == "Eventos"))).scalar_one_or_none()
    if not modulo_eventos:
        modulo_eventos = Modulo(nombre="Eventos", descripcion="Módulo de eventos")
        db.add(modulo_eventos)
        await db.flush()

    admin = (await db.execute(select(Miembro).where(Miembro.id == 1))).scalar_one_or_none()
    if not admin:
        admin = Miembro(
            id=1,
            nombre_completo="Admin Eventos",
            correo_electronico="admin_eventos@example.com",
            contrasena_hash=obtener_hash_contrasena("admin123"),
            id_rol=rol.id,
            id_hogar=hogar.id,
            estado=True,
        )
        db.add(admin)

    permiso = (
        await db.execute(
            select(Permiso).where(Permiso.id_rol == rol.id, Permiso.id_modulo == modulo_eventos.id)
        )
    ).scalar_one_or_none()
    if not permiso:
        permiso = Permiso(
            id_rol=rol.id,
            id_modulo=modulo_eventos.id,
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
async def test_crear_evento(client, admin_con_permiso_eventos, setup_rol_hogar):
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_eventos)}"}
    payload = {
        "titulo": "Cumpleaños",
        "descripcion": "Fiesta",
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "duracion_min": 120,
        "id_hogar": 1,
        "creado_por": admin_con_permiso_eventos.id,
    }
    resp = await client.post("/eventos/", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["titulo"] == "Cumpleaños"
    assert data["id_hogar"] == 1


@pytest.mark.asyncio
async def test_listar_eventos_por_hogar(client, admin_con_permiso_eventos, setup_rol_hogar):
    # Crear uno para asegurar datos
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_eventos)}"}
    await client.post(
        "/eventos/",
        json={
            "titulo": "Reunión",
            "descripcion": None,
            "fecha_hora": datetime.now(timezone.utc).isoformat(),
            "duracion_min": 60,
            "id_hogar": 1,
            "creado_por": admin_con_permiso_eventos.id,
        },
        headers=headers,
    )

    resp = await client.get("/eventos/hogar/1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

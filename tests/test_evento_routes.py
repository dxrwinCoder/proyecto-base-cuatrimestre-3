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
from models.tarea import Tarea
from models.evento import Evento
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


@pytest.mark.asyncio
async def test_actualizar_evento_admin(
    client, admin_con_permiso_eventos, setup_rol_hogar, db: AsyncSession
):
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_eventos)}"}
    crear_resp = await client.post(
        "/eventos/",
        json={
            "titulo": "Evento viejo",
            "descripcion": "desc",
            "fecha_hora": datetime.now(timezone.utc).isoformat(),
            "duracion_min": 30,
            "id_hogar": 1,
            "creado_por": admin_con_permiso_eventos.id,
        },
        headers=headers,
    )
    evento_id = crear_resp.json()["id"]

    nuevo_titulo = "Evento actualizado"
    nueva_fecha = datetime.now(timezone.utc) + timedelta(days=1)
    update_resp = await client.put(
        f"/eventos/{evento_id}",
        json={
            "titulo": nuevo_titulo,
            "duracion_min": 60,
            "fecha_hora": nueva_fecha.isoformat(),
            "estado": False,
        },
        headers=headers,
    )

    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["titulo"] == nuevo_titulo
    assert body["duracion_min"] == 60
    assert body["estado"] is False

    evento_db = await db.get(Evento, evento_id)
    assert evento_db.titulo == nuevo_titulo
    assert evento_db.estado is False


@pytest.mark.asyncio
async def test_eliminar_evento_admin(client, admin_con_permiso_eventos, setup_rol_hogar, db: AsyncSession):
    headers = {"Authorization": f"Bearer {token_para(admin_con_permiso_eventos)}"}
    crear_resp = await client.post(
        "/eventos/",
        json={
            "titulo": "Evento a eliminar",
            "descripcion": "desc",
            "fecha_hora": datetime.now(timezone.utc).isoformat(),
            "duracion_min": 45,
            "id_hogar": 1,
            "creado_por": admin_con_permiso_eventos.id,
        },
        headers=headers,
    )
    evento_id = crear_resp.json()["id"]

    delete_resp = await client.delete(f"/eventos/{evento_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["mensaje"] == "Evento eliminado"

    evento_db = await db.get(Evento, evento_id)
    assert evento_db.estado is False


@pytest.mark.asyncio
async def test_reasignar_miembro_en_tarea_evento(
    client: AsyncClient, db: AsyncSession, admin_con_permiso_eventos
):
    admin = admin_con_permiso_eventos
    headers = {"Authorization": f"Bearer {token_para(admin)}"}

    nuevo_miembro = Miembro(
        id=2,
        nombre_completo="Invitado Evento",
        correo_electronico="invitado@example.com",
        contrasena_hash=obtener_hash_contrasena("guest123"),
        id_rol=admin.id_rol,
        id_hogar=admin.id_hogar,
        estado=True,
    )
    db.add(nuevo_miembro)
    await db.flush()

    evento_payload = {
        "titulo": "Reunión semanal",
        "descripcion": "Planificación",
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "duracion_min": 45,
        "id_hogar": admin.id_hogar,
        "creado_por": admin.id,
    }
    evento_resp = await client.post("/eventos/", json=evento_payload, headers=headers)
    assert evento_resp.status_code == 201
    evento_id = evento_resp.json()["id"]

    tarea_payload = {
        "titulo": "Preparar sala",
        "categoria": "mantenimiento",
        "asignado_a": admin.id,
        "id_hogar": admin.id_hogar,
        "id_evento": evento_id,
    }
    tarea_resp = await client.post("/tareas/", json=tarea_payload, headers=headers)
    assert tarea_resp.status_code == 201
    tarea_id = tarea_resp.json()["id"]

    reasignacion = await client.put(
        f"/eventos/{evento_id}/tareas/{tarea_id}/miembro/{nuevo_miembro.id}",
        headers=headers,
    )

    assert reasignacion.status_code == 200
    assert reasignacion.json()["mensaje"] == "Miembro reasignado en la tarea del evento"

    tarea_db = await db.get(Tarea, tarea_id)
    assert tarea_db.asignado_a == nuevo_miembro.id

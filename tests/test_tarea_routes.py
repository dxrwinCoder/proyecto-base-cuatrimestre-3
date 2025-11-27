from sqlalchemy import select
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.modulo import Modulo
from models.permiso import Permiso
from models.hogar import Hogar
from models.tarea import Tarea
from models.comentario_tarea import ComentarioTarea
from utils.security import crear_token_acceso, obtener_hash_contrasena


@pytest_asyncio.fixture
async def client(db):
    # Sobrescribir la dependencia get_db para usar la base de datos de test
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Limpiar el override después del test
    app.dependency_overrides.clear()


def crear_token_test(miembro_id=1, id_hogar=1, id_rol=1):
    """Función helper para crear token de prueba"""
    # Esta versión acepta todos los argumentos necesarios para el payload
    return crear_token_acceso(
        {"sub": str(miembro_id), "id_hogar": id_hogar, "id_rol": id_rol}
    )


@pytest_asyncio.fixture
async def setup_miembro_con_permiso_tareas(db: AsyncSession, setup_rol_hogar):
    """
    Crea un Miembro (Admin, rol=1) y le da permisos CRUD
    completos para el módulo 'Tareas'.
    """
    # 1. Módulo 'Tareas'
    modulo_result = await db.execute(select(Modulo).where(Modulo.nombre == "Tareas"))
    modulo_tareas = modulo_result.scalar_one_or_none()
    if not modulo_tareas:
        modulo_tareas = Modulo(nombre="Tareas", descripcion="Módulo de Tareas")
        db.add(modulo_tareas)
        await db.flush()
        await db.refresh(modulo_tareas)

    # 2. Admin
    miembro_result = await db.execute(select(Miembro).where(Miembro.id == 1))
    admin = miembro_result.scalar_one_or_none()
    if not admin:
        admin = Miembro(
            id=1,
            nombre_completo="Admin Tareas Test",
            correo_electronico="admin_tareas@mail.com",
            contrasena_hash=obtener_hash_contrasena("admin123"),
            id_rol=1,
            id_hogar=1,
            estado=True,
        )
        db.add(admin)
        await db.flush()
        await db.refresh(admin)

    # 3. Permiso CRUD para Admin sobre 'Tareas'
    permiso_result = await db.execute(
        select(Permiso).where(
            Permiso.id_rol == 1, Permiso.id_modulo == modulo_tareas.id
        )
    )
    if not permiso_result.scalar_one_or_none():
        permiso = Permiso(
            id_rol=1,
            id_modulo=modulo_tareas.id,
            puede_crear=True,
            puede_leer=True,
            puede_actualizar=True,
            puede_eliminar=True,
        )
        db.add(permiso)
        await db.flush()

    yield admin


@pytest.mark.asyncio
async def test_crear_tarea_con_autenticacion(
    client: AsyncClient, setup_miembro_con_permiso_tareas
):

    admin = setup_miembro_con_permiso_tareas

    token = crear_token_test(
        miembro_id=admin.id,
        id_hogar=admin.id_hogar,
        id_rol=admin.id_rol,
    )
    headers = {"Authorization": f"Bearer {token}"}

    tarea_data = {
        "titulo": "Lavar platos",
        "categoria": "cocina",
        "asignado_a": 1,
        "id_hogar": 1,
    }

    response = await client.post("/tareas/", json=tarea_data, headers=headers)

    # Este assert ya está corregido a 201
    assert response.status_code == 201

    data = response.json()
    assert data["titulo"] == "Lavar platos"
    assert data["creado_por"] == admin.id  # ¡Verificamos que el endpoint lo asignó!


@pytest_asyncio.fixture
async def setup_miembro(db, setup_rol_hogar):
    from sqlalchemy import select

    # Crear módulo de prueba
    modulo_result = await db.execute(select(Modulo).where(Modulo.id == 1))
    modulo = modulo_result.scalar_one_or_none()
    if not modulo:
        modulo = Modulo(
            id=1,
            nombre="Tareas",
            descripcion="Módulo de tareas",
            estado=True,
        )
        db.add(modulo)

    # Crear permiso para crear tareas
    permiso_result = await db.execute(
        select(Permiso).where(Permiso.id_rol == 1, Permiso.id_modulo == 1)
    )
    permiso = permiso_result.scalar_one_or_none()
    if not permiso:
        permiso = Permiso(
            id_rol=1,
            id_modulo=1,
            puede_crear=True,
            puede_leer=True,
            puede_actualizar=True,
            puede_eliminar=True,
            estado=True,
        )
        db.add(permiso)

    # Crear miembro de prueba
    miembro_result = await db.execute(select(Miembro).where(Miembro.id == 1))
    miembro = miembro_result.scalar_one_or_none()
    if not miembro:
        miembro = Miembro(
            id=1,
            nombre_completo="Test User",
            correo_electronico="test@example.com",
            contrasena_hash="fake_hash",
            id_rol=1,
            id_hogar=1,
            estado=True,
        )
        db.add(miembro)

    await db.commit()
    await db.refresh(miembro)
    yield miembro


# @pytest.mark.asyncio
# async def test_crear_tarea_con_autenticacion(
#     client: AsyncClient, setup_miembro_con_permiso_tareas
# ):

#     admin = setup_miembro_con_permiso_tareas

#     token = crear_token_test(
#         miembro_id=admin.id, id_hogar=admin.id_hogar, id_rol=admin.id_rol
#     )
#     headers = {"Authorization": f"Bearer {token}"}

#     tarea_data = {
#         "titulo": "Lavar platos",
#         "categoria": "cocina",
#         "asignado_a": 1,
#         "id_hogar": 1,
#     }

#     response = await client.post("/tareas/", json=tarea_data, headers=headers)

#     # --- ¡PARCHE CORREGIDO! ---
#     assert response.status_code == 201  # Esperamos 201, no 200
#     # --- FIN DEL PARCHE ---

#     data = response.json()
#     assert data["titulo"] == "Lavar platos"
#     assert data["creado_por"] == admin.id


@pytest.mark.asyncio
async def test_actualizar_tarea_admin(
    client: AsyncClient, db: AsyncSession, setup_miembro_con_permiso_tareas
):
    admin = setup_miembro_con_permiso_tareas
    headers = {"Authorization": f"Bearer {crear_token_test(admin.id, admin.id_hogar, admin.id_rol)}"}

    otro = Miembro(
        id=2,
        nombre_completo="Nuevo asignado",
        correo_electronico="nuevo@mail.com",
        contrasena_hash=obtener_hash_contrasena("pass"),
        id_rol=admin.id_rol,
        id_hogar=admin.id_hogar,
        estado=True,
    )
    db.add(otro)
    await db.flush()

    crear = await client.post(
        "/tareas/",
        json={
            "titulo": "Tarea base",
            "categoria": "cocina",
            "asignado_a": admin.id,
            "id_hogar": admin.id_hogar,
        },
        headers=headers,
    )
    tarea_id = crear.json()["id"]

    actualizar = await client.put(
        f"/tareas/{tarea_id}",
        json={
            "titulo": "Tarea modificada",
            "descripcion": "Nueva descripcion",
            "asignado_a": otro.id,
            "ubicacion": "Sala",
        },
        headers=headers,
    )

    assert actualizar.status_code == 200
    body = actualizar.json()
    assert body["titulo"] == "Tarea modificada"
    assert body["asignado_a"] == otro.id

    tarea_db = await db.get(Tarea, tarea_id)
    assert tarea_db.asignado_a == otro.id
    assert tarea_db.descripcion == "Nueva descripcion"


@pytest.mark.asyncio
async def test_eliminar_tarea_admin(
    client: AsyncClient, db: AsyncSession, setup_miembro_con_permiso_tareas
):
    admin = setup_miembro_con_permiso_tareas
    headers = {"Authorization": f"Bearer {crear_token_test(admin.id, admin.id_hogar, admin.id_rol)}"}

    crear = await client.post(
        "/tareas/",
        json={
            "titulo": "Tarea a borrar",
            "categoria": "limpieza",
            "asignado_a": admin.id,
            "id_hogar": admin.id_hogar,
        },
        headers=headers,
    )
    tarea_id = crear.json()["id"]

    borrar = await client.delete(f"/tareas/{tarea_id}", headers=headers)
    assert borrar.status_code == 200
    assert borrar.json()["mensaje"] == "Tarea eliminada"

    tarea_db = await db.get(Tarea, tarea_id)
    assert tarea_db.estado is False


@pytest.mark.asyncio
async def test_cambiar_estado_tarea_rol2(client: AsyncClient, db: AsyncSession, setup_miembro_con_permiso_tareas):
    admin = setup_miembro_con_permiso_tareas
    rol2 = Rol(id=2, nombre="Colaborador", descripcion="rol lector", estado=True)
    miembro2 = Miembro(
        id=3,
        nombre_completo="Miembro rol2",
        correo_electronico="rol2@mail.com",
        contrasena_hash=obtener_hash_contrasena("pass"),
        id_rol=rol2.id,
        id_hogar=admin.id_hogar,
        estado=True,
    )
    db.add_all([rol2, miembro2])
    await db.flush()

    headers_admin = {"Authorization": f"Bearer {crear_token_test(admin.id, admin.id_hogar, admin.id_rol)}"}
    crear = await client.post(
        "/tareas/",
        json={
            "titulo": "Tarea rol2",
            "categoria": "compras",
            "asignado_a": miembro2.id,
            "id_hogar": admin.id_hogar,
        },
        headers=headers_admin,
    )
    tarea_id = crear.json()["id"]

    headers_rol2 = {"Authorization": f"Bearer {crear_token_test(miembro2.id, miembro2.id_hogar, miembro2.id_rol)}"}
    cambio = await client.put(
        f"/tareas/{tarea_id}/estado",
        json={"estado_actual": "completada"},
        headers=headers_rol2,
    )
    assert cambio.status_code == 200
    assert cambio.json()["estado_actual"] == "completada"


@pytest.mark.asyncio
async def test_actualizar_comentario_tarea_rol2(
    client: AsyncClient, db: AsyncSession, setup_miembro_con_permiso_tareas
):
    admin = setup_miembro_con_permiso_tareas
    rol2 = Rol(id=2, nombre="Invitado", descripcion="rol colaborador", estado=True)
    miembro = Miembro(
        id=4,
        nombre_completo="Comentador",
        correo_electronico="comentador@mail.com",
        contrasena_hash=obtener_hash_contrasena("pass"),
        id_rol=rol2.id,
        id_hogar=admin.id_hogar,
        estado=True,
    )
    db.add_all([rol2, miembro])
    await db.flush()

    headers_admin = {"Authorization": f"Bearer {crear_token_test(admin.id, admin.id_hogar, admin.id_rol)}"}
    tarea_resp = await client.post(
        "/tareas/",
        json={
            "titulo": "Tarea con comentario",
            "categoria": "cocina",
            "asignado_a": miembro.id,
            "id_hogar": admin.id_hogar,
        },
        headers=headers_admin,
    )
    tarea_id = tarea_resp.json()["id"]

    headers_miembro = {"Authorization": f"Bearer {crear_token_test(miembro.id, miembro.id_hogar, miembro.id_rol)}"}
    comentario_resp = await client.post(
        "/comentarios-tarea/",
        json={"id_tarea": tarea_id, "contenido": "texto original"},
        headers=headers_miembro,
    )
    comentario_id = comentario_resp.json()["id"]

    update_resp = await client.put(
        f"/comentarios-tarea/{comentario_id}",
        json={"contenido": "texto editado"},
        headers=headers_miembro,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["contenido"] == "texto editado"

    comentario_db = await db.get(ComentarioTarea, comentario_id)
    assert comentario_db.contenido == "texto editado"


@pytest.mark.asyncio
async def test_cambiar_estado_tarea(client: AsyncClient, db: AsyncSession, setup_miembro_con_permiso_tareas):
    admin = setup_miembro_con_permiso_tareas
    headers = {
        "Authorization": f"Bearer {crear_token_test(admin.id, admin.id_hogar, admin.id_rol)}"
    }

    nueva_tarea = {
        "titulo": "Revisar inventario",
        "categoria": "compras",
        "asignado_a": admin.id,
        "id_hogar": admin.id_hogar,
    }

    creada = await client.post("/tareas/", json=nueva_tarea, headers=headers)
    assert creada.status_code == 201
    tarea_id = creada.json()["id"]

    actualizada = await client.put(
        f"/tareas/{tarea_id}/estado",
        json={"estado_actual": "en_progreso"},
        headers=headers,
    )

    assert actualizada.status_code == 200
    assert actualizada.json()["estado_actual"] == "en_progreso"

    tarea_db = await db.get(Tarea, tarea_id)
    assert tarea_db.estado_actual == "en_progreso"

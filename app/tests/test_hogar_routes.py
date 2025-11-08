# tests/test_hogar_routes.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from main import app
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.modulo import Modulo
from models.permiso import Permiso
from models.hogar import Hogar
from utils.security import crear_token_acceso, obtener_hash_contrasena

# --- Fixtures de Cliente y Token (¡Necesarias!) ---


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """Fixture para crear cliente HTTP con BD de test"""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def crear_token_test(miembro_id=1, id_hogar=1, id_rol=1):
    """Función helper para crear token de prueba"""
    return crear_token_acceso(
        {"sub": str(miembro_id), "id_hogar": id_hogar, "id_rol": id_rol}
    )


@pytest_asyncio.fixture
async def setup_admin_con_permisos_hogar(db: AsyncSession, setup_rol_hogar):
    """
    Crea un Miembro (Admin, rol=1) y le da permisos CRUD
    completos para el módulo 'Hogares'.
    (Usa el 'setup_rol_hogar' de conftest.py)
    """

    # 1. Módulo 'Hogares'
    modulo_result = await db.execute(select(Modulo).where(Modulo.nombre == "Hogares"))
    modulo_hogares = modulo_result.scalar_one_or_none()
    if not modulo_hogares:
        modulo_hogares = Modulo(nombre="Hogares", descripcion="Módulo de Hogares")
        db.add(modulo_hogares)
        await db.flush()
        await db.refresh(modulo_hogares)

    # 2. Admin
    miembro_result = await db.execute(select(Miembro).where(Miembro.id == 1))
    admin = miembro_result.scalar_one_or_none()
    if not admin:
        admin = Miembro(
            id=1,
            nombre_completo="Admin Hogar Test",
            correo_electronico="admin_hogar@example.com",
            contrasena_hash=obtener_hash_contrasena("admin123"),
            id_rol=1,  # Admin
            id_hogar=1,  # Hogar de conftest
            estado=True,
        )
        db.add(admin)
        await db.flush()
        await db.refresh(admin)

    # 3. Permiso CRUD para Admin sobre 'Hogares'
    permiso_result = await db.execute(
        select(Permiso).where(
            Permiso.id_rol == 1, Permiso.id_modulo == modulo_hogares.id
        )
    )
    if not permiso_result.scalar_one_or_none():
        permiso = Permiso(
            id_rol=1,
            id_modulo=modulo_hogares.id,
            puede_crear=True,
            puede_leer=True,
            puede_actualizar=True,
            puede_eliminar=True,
        )
        db.add(permiso)
        await db.flush()

    yield admin


@pytest_asyncio.fixture
async def setup_usuario_sin_permisos(db: AsyncSession, setup_rol_hogar):
    """Crea un usuario normal (rol=2) sin permisos especiales"""

    rol_user_result = await db.execute(select(Rol).where(Rol.id == 2))
    rol_user = rol_user_result.scalar_one_or_none()
    if not rol_user:
        rol_user = Rol(id=2, nombre="Usuario_Test", descripcion="Usuario normal")
        db.add(rol_user)

    hogar_user_result = await db.execute(select(Hogar).where(Hogar.id == 2))
    hogar_user = hogar_user_result.scalar_one_or_none()
    if not hogar_user:
        hogar_user = Hogar(id=2, nombre="Hogar 2")
        db.add(hogar_user)

    await db.flush()

    usuario = Miembro(
        id=2,
        nombre_completo="Usuario Sin Permisos",
        correo_electronico="user@example.com",
        contrasena_hash=obtener_hash_contrasena("user123"),
        id_rol=rol_user.id,
        id_hogar=hogar_user.id,
        estado=True,
    )
    db.add(usuario)
    await db.flush()
    await db.refresh(usuario)
    yield usuario


# --- ¡LOS TESTS! ---


@pytest.mark.asyncio
async def test_crear_hogar_con_permiso(
    client: AsyncClient, setup_admin_con_permisos_hogar
):
    """Prueba que un Admin PUEDE crear un hogar (201 Created)"""
    token = crear_token_test(miembro_id=setup_admin_con_permisos_hogar.id)
    headers = {"Authorization": f"Bearer {token}"}

    datos_hogar = {"nombre": f"Hogar Admin {uuid.uuid4().hex[:6]}"}

    response = await client.post("/hogares/", json=datos_hogar, headers=headers)

    assert response.status_code == 201  # ¡201 Creado!
    data = response.json()
    assert data["nombre"] == datos_hogar["nombre"]


@pytest.mark.asyncio
async def test_crear_hogar_duplicado_ruta(
    client: AsyncClient, setup_admin_con_permisos_hogar
):
    """Prueba que la ruta maneja el error de duplicado (400)"""
    token = crear_token_test(miembro_id=setup_admin_con_permisos_hogar.id)
    headers = {"Authorization": f"Bearer {token}"}
    datos_hogar = {"nombre": f"Hogar Duplicado Ruta {uuid.uuid4().hex[:6]}"}

    # Creamos el primero
    response1 = await client.post("/hogares/", json=datos_hogar, headers=headers)
    assert response1.status_code == 201

    # Creamos el segundo
    response2 = await client.post("/hogares/", json=datos_hogar, headers=headers)
    assert response2.status_code == 400
    assert "El nombre del hogar ya existe" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_crear_hogar_sin_token(client: AsyncClient):
    """Prueba el "Bouncer": No se puede crear un hogar sin token (401)"""
    datos_hogar = {"nombre": "Hogar Sin Token"}
    response = await client.post("/hogares/", json=datos_hogar)
    assert response.status_code == 401  # ¡Probando la seguridad!


@pytest.mark.asyncio
async def test_crear_hogar_sin_permiso(client: AsyncClient, setup_usuario_sin_permisos):
    """Prueba el "Bouncer": Un usuario normal NO puede crear un hogar (403)"""
    token = crear_token_test(
        miembro_id=setup_usuario_sin_permisos.id,
        id_hogar=setup_usuario_sin_permisos.id_hogar,
        id_rol=setup_usuario_sin_permisos.id_rol,
    )
    headers = {"Authorization": f"Bearer {token}"}

    datos_hogar = {"nombre": "Hogar Falla Permiso"}

    response = await client.post("/hogares/", json=datos_hogar, headers=headers)

    assert response.status_code == 403  # ¡Probando los permisos!


@pytest.mark.asyncio
async def test_ver_hogar_no_encontrado(
    client: AsyncClient, setup_admin_con_permisos_hogar
):
    """Prueba el error 404 si el hogar no existe"""
    token = crear_token_test(miembro_id=setup_admin_con_permisos_hogar.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/hogares/9999", headers=headers)

    assert response.status_code == 404

# tests/test_permiso_routes.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
async def setup_admin_con_permisos_permisos(db: AsyncSession, setup_rol_hogar):
    """
    Crea un Admin (rol=1) y le da permisos CRUD
    completos para el módulo 'Permisos'.
    """

    # 1. Módulo 'Permisos'
    modulo_result = await db.execute(select(Modulo).where(Modulo.nombre == "Permisos"))
    modulo_permisos = modulo_result.scalar_one_or_none()
    if not modulo_permisos:
        modulo_permisos = Modulo(nombre="Permisos", descripcion="Módulo de Permisos")
        db.add(modulo_permisos)
        await db.flush()
        await db.refresh(modulo_permisos)

    # 2. Módulo 'Hogares' (para asignar permisos *a*)
    modulo_hogares_result = await db.execute(
        select(Modulo).where(Modulo.nombre == "Hogares")
    )
    modulo_hogares = modulo_hogares_result.scalar_one_or_none()
    if not modulo_hogares:
        modulo_hogares = Modulo(nombre="Hogares", descripcion="Para asignar permisos")
        db.add(modulo_hogares)
        await db.flush()
        await db.refresh(modulo_hogares)

    # 3. Admin
    miembro_result = await db.execute(select(Miembro).where(Miembro.id == 1))
    admin = miembro_result.scalar_one_or_none()
    if not admin:
        admin = Miembro(
            id=1,
            nombre_completo="Admin Permiso Test",
            correo_electronico="admin_permiso@example.com",
            contrasena_hash=obtener_hash_contrasena("admin123"),
            id_rol=1,  # Admin
            id_hogar=1,  # Hogar de conftest
            estado=True,
        )
        db.add(admin)
        await db.flush()
        await db.refresh(admin)

    # 4. Permiso para el Admin sobre 'Permisos'
    permiso_result = await db.execute(
        select(Permiso).where(
            Permiso.id_rol == 1, Permiso.id_modulo == modulo_permisos.id
        )
    )
    if not permiso_result.scalar_one_or_none():
        permiso = Permiso(
            id_rol=1,
            id_modulo=modulo_permisos.id,
            puede_crear=True,
        )
        db.add(permiso)
        await db.flush()

    yield {"admin": admin, "modulo_hogares": modulo_hogares}


@pytest.mark.asyncio
async def test_asignar_permiso_con_permiso(
    client: AsyncClient, setup_admin_con_permisos_permisos
):
    """Prueba que un Admin PUEDE asignar un permiso (201 Created)"""
    admin = setup_admin_con_permisos_permisos["admin"]
    modulo_hogares = setup_admin_con_permisos_permisos["modulo_hogares"]

    token = crear_token_test(miembro_id=admin.id, id_rol=admin.id_rol)
    headers = {"Authorization": f"Bearer {token}"}

    datos_permiso = {
        "id_rol": admin.id_rol,
        "id_modulo": modulo_hogares.id,  # Asignando permiso sobre 'Hogares'
        "puede_crear": True,
        "puede_leer": True,
    }

    response = await client.post("/permisos/", json=datos_permiso, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["id_rol"] == admin.id_rol
    assert data["id_modulo"] == modulo_hogares.id
    assert data["puede_crear"] is True


@pytest.mark.asyncio
async def test_asignar_permiso_sin_token(
    client: AsyncClient, setup_admin_con_permisos_permisos
):
    """Prueba el "Bouncer": No se puede asignar permiso sin token (401)"""
    admin = setup_admin_con_permisos_permisos["admin"]
    modulo_hogares = setup_admin_con_permisos_permisos["modulo_hogares"]

    datos_permiso = {
        "id_rol": admin.id_rol,
        "id_modulo": modulo_hogares.id,
        "puede_crear": True,
    }

    response = await client.post("/permisos/", json=datos_permiso)
    assert response.status_code == 401  # ¡Probando la seguridad!

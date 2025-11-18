# tests/test_auth_routes.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from main import app  # Asumiendo que su app se llama 'app' en 'main.py'
from db.database import get_db
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from models.permiso import Permiso
from models.modulo import Modulo  # ¡Necesario para verificar permisos!
from schemas.auth import MiembroRegistro  # Asegurarse que el schema esté bien
from utils.security import obtener_hash_contrasena


# --- Fixture de Cliente (ya la tenía, pero "calibrada") ---
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


# --- Fixture de Setup (MODIFICADA) ---
@pytest_asyncio.fixture
async def setup_datos_base(db: AsyncSession):
    """
    Crea los datos MÍNIMOS que la app necesita para CUALQUIER registro:
    - 1. Un Rol "Administrador" (id=1)
    - 2. Un Rol "Hijo" (id=2)
    - 3. Un Hogar "Principal" (id=1) (para registrar usuarios normales)
    - 4. Módulos (para que la creación de permisos funcione)
    """
    rol_admin = Rol(id=1, nombre="Administrador")
    rol_hijo = Rol(id=2, nombre="Hijo")
    hogar_base = Hogar(id=1, nombre="Hogar Principal")

    # Crear Módulos
    modulos = [
        Modulo(nombre="Tareas"),
        Modulo(nombre="Miembros"),
        Modulo(nombre="Hogares"),
        Modulo(nombre="Roles"),
        Modulo(nombre="Permisos"),
        Modulo(nombre="Eventos"),
        # ... (añadir todos los módulos de su script SQL)
    ]

    db.add_all([rol_admin, rol_hijo, hogar_base] + modulos)
    await db.flush()

    return {
        "rol_admin": rol_admin,
        "rol_hijo": rol_hijo,
        "hogar_base": hogar_base,
        "modulos_count": len(modulos),
    }


# --- ¡INICIO DE LOS TESTS "CALIBRADOS"! ---


@pytest.mark.asyncio
async def test_registro_admin_crea_hogar_y_permisos(
    client: AsyncClient, db: AsyncSession, setup_datos_base
):
    """
    PRUEBA CLAVE: Flujo 1 (Admin Fundador)
    Verifica que al registrar un Admin (Rol 1) sin hogar:
    1. Se crea el Admin.
    2. Se crea un NUEVO Hogar (ej. "Hogar de Admin...").
    3. Se asigna el Admin a ese nuevo Hogar.
    4. Se crean todos los Permisos para el Rol 1.
    """
    datos_registro_admin = {
        "nombre_completo": "Admin Fundador",
        "correo_electronico": "admin.fundador@example.com",
        "contrasena": "admin12345",
        "id_rol": 1,
        # ¡No se envía id_hogar!
    }

    # 1. Ejecutar el registro
    response = await client.post("/auth/registro", json=datos_registro_admin)

    # 2. Verificar la Respuesta
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["id_miembro"] is not None
    assert data["id_hogar"] != 1  # ¡Debe ser un ID nuevo (ej. 2)!
    assert data["rol"]["nombre"] == "Administrador"

    nuevo_miembro_id = data["id_miembro"]
    nuevo_hogar_id = data["id_hogar"]

    # 3. Verificar en la Base de Datos
    miembro_creado = await db.get(Miembro, nuevo_miembro_id)
    hogar_creado = await db.get(Hogar, nuevo_hogar_id)

    assert miembro_creado is not None
    assert miembro_creado.id_rol == 1
    assert miembro_creado.id_hogar == nuevo_hogar_id  # Verificación de asignación

    assert hogar_creado is not None
    assert (
        hogar_creado.nombre == f"Hogar de {miembro_creado.nombre_completo}"
    )  # Lógica del servicio

    # 4. Verificar Permisos
    permisos = (
        (await db.execute(select(Permiso).where(Permiso.id_rol == 1))).scalars().all()
    )
    assert len(permisos) == setup_datos_base["modulos_count"]
    assert permisos[0].puede_crear == True  # Verificar que los permisos se dieron


@pytest.mark.asyncio
async def test_registro_usuario_normal_exitoso(
    client: AsyncClient, db: AsyncSession, setup_datos_base
):
    """
    PRUEBA CLAVE: Flujo 2 (Usuario Normal)
    Verifica que un usuario normal (Rol 2) SE PUEDE registrar
    si especifica un hogar existente (id_hogar: 1).
    """
    datos_registro_hijo = {
        "nombre_completo": "Hijo 1",
        "correo_electronico": "hijo1@example.com",
        "contrasena": "user12345",
        "id_rol": 2,
        "id_hogar": 1,  # ¡Hogar existente del setup!
    }

    response = await client.post("/auth/registro", json=datos_registro_hijo)

    assert response.status_code == 201
    data = response.json()
    assert data["id_hogar"] == 1
    assert data["rol"]["nombre"] == "Hijo"


@pytest.mark.asyncio
async def test_registro_usuario_falla_sin_hogar(client: AsyncClient, setup_datos_base):
    """
    PRUEBA CLAVE: Flujo 2 (Fallo)
    Verifica que un usuario normal (Rol 2) NO PUEDE registrarse
    si omite el 'id_hogar'.
    """
    datos_registro_hijo_fallo = {
        "nombre_completo": "Hijo 2 Fallido",
        "correo_electronico": "hijo2@example.com",
        "contrasena": "user12345",
        "id_rol": 2,
        # ¡No se envía id_hogar!
    }

    response = await client.post("/auth/registro", json=datos_registro_hijo_fallo)

    assert response.status_code == 400
    data = response.json()
    assert "obligatorio para registrar un miembro no-administrador" in data["detail"]


@pytest.mark.asyncio
async def test_registro_admin_falla_con_hogar_existente(
    client: AsyncClient, setup_datos_base
):
    """
    PRUEBA CLAVE: Flujo 1 (Fallo)
    Verifica que un Admin (Rol 1) NO PUEDE registrarse
    si especifica un 'id_hogar' (como en su prueba fallida).
    """
    datos_registro_admin_fallo = {
        "nombre_completo": "Admin Fallido",
        "correo_electronico": "admin.fallido@example.com",
        "contrasena": "admin12345",
        "id_rol": 1,
        "id_hogar": 1,  # ¡Un admin no debe especificar hogar!
    }

    response = await client.post("/auth/registro", json=datos_registro_admin_fallo)

    assert response.status_code == 400
    data = response.json()
    assert "no debe incluir un 'id_hogar'" in data["detail"]

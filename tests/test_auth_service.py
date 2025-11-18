# tests/test_auth_service.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# ¡Importar todos los modelos y schemas necesarios!
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from models.modulo import Modulo
from models.permiso import Permiso
from schemas.auth import MiembroRegistro

# ¡Importar los servicios que vamos a probar!
from services.auth_service import crear_miembro, autenticar_miembro

# ¡Importar el servicio que 'crear_miembro' necesita!
from services.hogar_service import crear_hogar_interno


# --- Fixture "Calibrada" (La misma de test_auth_routes.py) ---
@pytest_asyncio.fixture
async def setup_datos_base(db: AsyncSession):
    """
    Crea los datos MÍNIMOS que la app necesita:
    - Roles (Admin y Hijo)
    - Módulos (Tareas, Miembros, etc.)
    """
    rol_admin = Rol(id=1, nombre="Administrador")
    rol_hijo = Rol(id=2, nombre="Hijo")

    # ¡Importante! 'crear_miembro' (admin) crea su propio hogar,
    # pero 'crear_miembro' (usuario) necesita que un hogar (ej. id=1) ya exista.
    hogar_base_para_usuarios = Hogar(id=1, nombre="Hogar Base Usuarios")

    modulos = [
        Modulo(nombre="Tareas"),
        Modulo(nombre="Miembros"),
        Modulo(nombre="Hogares"),
        Modulo(nombre="Roles"),
        Modulo(nombre="Permisos"),
        Modulo(nombre="Eventos"),
        # ... (todos los módulos de su script SQL)
    ]

    db.add_all([rol_admin, rol_hijo, hogar_base_para_usuarios] + modulos)
    await db.flush()

    return {"modulos_count": len(modulos)}


# --- ¡Tests "Calibrados"! ---


@pytest.mark.asyncio
async def test_crear_miembro_admin_flujo_completo(db: AsyncSession, setup_datos_base):
    """
    PRUEBA CLAVE: Flujo 1 (Admin Fundador)
    Prueba 'services.auth_service.crear_miembro' con id_rol=1.
    Debe:
    1. Crear un Hogar nuevo (ej. "Hogar de Admin...").
    2. Crear el Miembro Admin.
    3. Asignar el Admin al nuevo Hogar.
    4. Crear todos los Permisos para el rol 1.
    """
    datos_admin = MiembroRegistro(
        nombre_completo="Admin Servicio Test",
        correo_electronico="admin.servicio@example.com",
        contrasena="admin12345",
        id_rol=1,
        id_hogar=None,  # ¡Importante! El Admin no envía hogar
    )

    # 1. Ejecutar el servicio
    miembro_creado = await crear_miembro(db, datos_admin)

    # 2. Verificar el Miembro
    assert miembro_creado is not None
    assert miembro_creado.id_rol == 1
    assert miembro_creado.nombre_completo == "Admin Servicio Test"

    # 3. Verificar el Hogar Nuevo
    # (El servicio crea un hogar nuevo, que no será el id=1)
    assert miembro_creado.id_hogar != 1
    hogar_nuevo = await db.get(Hogar, miembro_creado.id_hogar)
    assert hogar_nuevo is not None
    assert hogar_nuevo.nombre == "Hogar de Admin Servicio Test"

    # 4. Verificar los Permisos
    permisos = (
        (await db.execute(select(Permiso).where(Permiso.id_rol == 1))).scalars().all()
    )
    assert len(permisos) == setup_datos_base["modulos_count"]
    assert permisos[0].puede_crear is True


@pytest.mark.asyncio
async def test_crear_miembro_usuario_flujo_simple(db: AsyncSession, setup_datos_base):
    """
    PRUEBA CLAVE: Flujo 2 (Usuario Normal)
    Prueba 'services.auth_service.crear_miembro' con id_rol=2.
    Debe:
    1. Asignar al 'id_hogar=1' existente.
    2. NO crear un hogar nuevo.
    3. NO crear permisos.
    """
    datos_hijo = MiembroRegistro(
        nombre_completo="Hijo Servicio Test",
        correo_electronico="hijo.servicio@example.com",
        contrasena="user12345",
        id_rol=2,
        id_hogar=1,  # ¡Hogar existente!
    )

    miembro_creado = await crear_miembro(db, datos_hijo)

    assert miembro_creado is not None
    assert miembro_creado.id_rol == 2
    assert miembro_creado.id_hogar == 1  # Asignado al hogar correcto


@pytest.mark.asyncio
async def test_crear_miembro_admin_falla_con_hogar(db: AsyncSession, setup_datos_base):
    """
    PRUEBA DE FALLO: Admin no puede enviar 'id_hogar'
    """
    datos_admin_fallo = MiembroRegistro(
        nombre_completo="Admin Fallo",
        correo_electronico="admin.fallo@example.com",
        contrasena="admin12345",
        id_rol=1,
        id_hogar=1,  # ¡Error!
    )

    with pytest.raises(ValueError, match="no debe incluir un 'id_hogar'"):
        await crear_miembro(db, datos_admin_fallo)


@pytest.mark.asyncio
async def test_crear_miembro_usuario_falla_sin_hogar(
    db: AsyncSession, setup_datos_base
):
    """
    PRUEBA DE FALLO: Usuario (rol 2) debe enviar 'id_hogar'
    """
    datos_hijo_fallo = MiembroRegistro(
        nombre_completo="Hijo Fallo",
        correo_electronico="hijo.fallo@example.com",
        contrasena="user12345",
        id_rol=2,
        id_hogar=None,  # ¡Error!
    )

    with pytest.raises(ValueError, match="obligatorio para registrar un miembro"):
        await crear_miembro(db, datos_hijo_fallo)

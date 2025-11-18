# tests/test_miembro_service.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# ¡Importar modelos y schemas!
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from models.modulo import Modulo
from models.permiso import Permiso
from schemas.miembro import MiembroCreate

# ¡Importar el servicio que vamos a probar!
from services.miembro_service import crear_miembro, obtener_miembro


# --- Fixture "Calibrada" ---
@pytest_asyncio.fixture
async def setup_datos_miembro(db: AsyncSession):
    """
    Crea los datos base para probar el 'miembro_service':
    - Rol 1 (Admin), Rol 2 (Hijo)
    - Hogar 1 (Hogar Admin)
    - Módulos (para probar la creación de permisos)
    """
    rol_admin = Rol(id=1, nombre="Administrador")
    rol_hijo = Rol(id=2, nombre="Usuario")
    hogar1 = Hogar(id=1, nombre="Hogar 1")

    modulos = [Modulo(nombre="Tareas"), Modulo(nombre="Miembros")]

    db.add_all([rol_admin, rol_hijo, hogar1] + modulos)
    await db.flush()
    return {"modulos_count": len(modulos)}


@pytest.mark.asyncio
async def test_crear_miembro_normal_por_admin(db: AsyncSession, setup_datos_miembro):
    """
    Prueba que el servicio 'crear_miembro' (de Admin)
    crea un usuario normal (Rol 2) correctamente.
    """
    # (Pydantic v1 usa .dict(), v2 usa .model_dump())
    # Usamos un dict plano porque el servicio 'miembro_service'
    # (legacy) que me pasó recibía un dict.
    data_hijo = {
        "nombre_completo": "Hijo Creado por Admin",
        "correo_electronico": "hijo.admin@example.com",
        "contrasena": "user12345",
        "id_rol": 2,
        "id_hogar": 1,
    }

    miembro_creado = await crear_miembro(db, data_hijo)

    assert miembro_creado is not None
    assert miembro_creado.id_rol == 2
    assert miembro_creado.id_hogar == 1


@pytest.mark.asyncio
async def test_crear_miembro_admin_por_admin(db: AsyncSession, setup_datos_miembro):
    """
    PRUEBA CLAVE: Flujo 3 (Admin creando Admin)
    Prueba que el servicio 'crear_miembro' (de Admin)
    asigna permisos si el nuevo miembro es (Rol 1).
    """
    data_admin2 = {
        "nombre_completo": "Admin Secundario",
        "correo_electronico": "admin2@example.com",
        "contrasena": "admin54321",
        "id_rol": 1,
        "id_hogar": 1,
    }

    miembro_creado = await crear_miembro(db, data_admin2)

    assert miembro_creado is not None
    assert miembro_creado.id_rol == 1

    # Verificar que los permisos se crearon
    permisos = (
        (await db.execute(select(Permiso).where(Permiso.id_rol == 1))).scalars().all()
    )
    assert len(permisos) == setup_datos_miembro["modulos_count"]
    assert permisos[0].puede_actualizar is True


@pytest.mark.asyncio
async def test_crear_miembro_falla_correo_duplicado(
    db: AsyncSession, setup_datos_miembro
):
    """
    Prueba la validación de correo duplicado.
    """
    data1 = {
        "nombre_completo": "Miembro 1",
        "correo_electronico": "duplicado@example.com",
        "contrasena": "user12345",
        "id_rol": 2,
        "id_hogar": 1,
    }
    await crear_miembro(db, data1)

    data2 = {
        "nombre_completo": "Miembro 2",
        "correo_electronico": "duplicado@example.com",  # Mismo correo
        "contrasena": "user54321",
        "id_rol": 2,
        "id_hogar": 1,
    }

    with pytest.raises(ValueError, match="El correo electrónico ya está registrado"):
        await crear_miembro(db, data2)

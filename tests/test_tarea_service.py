import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.miembro import Miembro
from models.hogar import Hogar
from models.rol import Rol
from models.notificacion import Notificacion
from sqlalchemy import select
from schemas.tarea import TareaCreate

from services.tarea_service import crear_tarea, actualizar_estado_tarea


@pytest_asyncio.fixture
async def setup_miembro_admin(db: AsyncSession):
    """Crea un Hogar, un Rol y un Miembro (Admin) base"""

    # --- ¡PARCHE 1.1! ---
    # ¡Se pasan con nombre (kwargs), no posicionales!
    hogar = Hogar(id=1, nombre="Hogar Test")
    rol = Rol(id=1, nombre="Admin Test")
    admin = Miembro(
        id=1,
        nombre_completo="Admin Tareas",
        correo_electronico="admin_tareas@mail.com",
        contrasena_hash="123",
        id_rol=1,
        id_hogar=1,
    )

    db.add_all([hogar, rol, admin])
    await db.flush()
    return admin


@pytest.mark.asyncio
async def test_crear_tarea(db: AsyncSession, setup_miembro_admin):

    creador = setup_miembro_admin  # La fixture ya está resuelta
    creador_id = creador.id

    data = TareaCreate(
        titulo="Lavar platos",
        categoria="cocina",
        asignado_a=1,
        id_hogar=1,
    )

    tarea = await crear_tarea(db, data, creador_id)

    assert tarea is not None
    assert tarea.titulo == "Lavar platos"


@pytest.mark.asyncio
async def test_actualizar_estado_a_completada(db: AsyncSession, setup_miembro_admin):

    # --- ¡PARCHE 1.2! ---
    creador = setup_miembro_admin
    creador_id = creador.id
    # --- FIN DEL PARCHE ---

    data = TareaCreate(titulo="Test", categoria="limpieza", asignado_a=1, id_hogar=1)

    tarea = await crear_tarea(db, data, creador_id)

    tarea_actualizada = await actualizar_estado_tarea(
        db, tarea_id=tarea.id, nuevo_estado="completada", miembro_id=creador_id
    )

    assert tarea_actualizada.estado_actual == "completada"
    assert tarea_actualizada.tiempo_total_segundos is not None

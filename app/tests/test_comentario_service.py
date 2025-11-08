import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.tarea import TareaCreate
from schemas.comentario_tarea import ComentarioTareaCreate  # ¡Importar schema!
from services.tarea_service import crear_tarea, agregar_comentario_a_tarea
from models.miembro import Miembro
from models.hogar import Hogar
from models.rol import Rol
from models.notificacion import Notificacion
from sqlalchemy import select


@pytest_asyncio.fixture  # Usar '@pytest_asyncio.fixture'
async def setup_tarea_con_creador_y_asignado(db: AsyncSession):
    """
    Crea un Hogar, un Rol, un Creador (Admin, id=1)
    y un Asignado (Usuario, id=2)
    """

    # --- ¡PARCHE CORREGIDO! (Usar kwargs para __init__) ---
    hogar = Hogar(id=1, nombre="Hogar Test")
    rol_admin = Rol(id=1, nombre="Admin Test")
    rol_user = Rol(id=2, nombre="User Test")

    creador = Miembro(
        id=1,
        nombre_completo="Admin Creador",
        correo_electronico="admin@mail.com",
        contrasena_hash="123",
        id_rol=1,
        id_hogar=1,
    )
    asignado = Miembro(
        id=2,
        nombre_completo="Usuario Asignado",
        correo_electronico="user@mail.com",
        contrasena_hash="123",
        id_rol=2,
        id_hogar=1,
    )
    # --- FIN DEL PARCHE ---

    db.add_all([hogar, rol_admin, rol_user, creador, asignado])
    await db.flush()

    data_tarea = TareaCreate(
        titulo="Tarea para Comentar",
        categoria="cocina",
        asignado_a=asignado.id,
        id_hogar=hogar.id,
    )

    tarea = await crear_tarea(db, data_tarea, creador_id=creador.id)

    return {"tarea": tarea, "creador": creador, "asignado": asignado}


@pytest.mark.asyncio
async def test_agregar_comentario_y_notifica(
    db: AsyncSession, setup_tarea_con_creador_y_asignado
):

    # --- ¡PARCHE CORREGIDO! (No usar 'await' en la fixture) ---
    setup_data = setup_tarea_con_creador_y_asignado  # La fixture ya está resuelta
    tarea = setup_data["tarea"]
    creador = setup_data["creador"]
    asignado = setup_data["asignado"]
    # --- FIN DEL PARCHE ---

    datos_comentario = ComentarioTareaCreate(
        id_tarea=tarea.id, contenido="¡Ya casi termino!"
    )

    comentario = await agregar_comentario_a_tarea(
        db, datos_comentario, miembro_id=asignado.id
    )

    assert comentario is not None
    assert comentario.contenido == "¡Ya casi termino!"

    # Verificar notificación
    notifs = (await db.execute(select(Notificacion))).scalars().all()
    assert len(notifs) >= 1  # Debe haber al menos 1 (la de nuevo comentario)

    notif_comentario = [n for n in notifs if n.tipo == "nuevo_comentario"][0]
    assert notif_comentario.id_miembro_destino == creador.id
    assert notif_comentario.id_miembro_origen == asignado.id

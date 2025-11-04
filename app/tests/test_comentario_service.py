import pytest
from models.tarea import Tarea
from services.tarea_service import crear_tarea
from services.comentario_tarea_service import agregar_comentario_a_tarea


@pytest.mark.asyncio
async def test_agregar_comentario(db):
    # Crear tarea primero
    tarea_data = {
        "titulo": "Test",
        "categoria": "cocina",
        "asignado_a": 1,
        "id_hogar": 1,
    }
    tarea = await crear_tarea(db, tarea_data)

    # Agregar comentario
    comentario_data = {
        "id_tarea": tarea.id,
        "contenido": "Ya terminé",
        "id_miembro": 2,
    }
    comentario = await agregar_comentario_a_tarea(db, comentario_data)
    assert comentario.id is not None
    assert comentario.contenido == "Ya terminé"

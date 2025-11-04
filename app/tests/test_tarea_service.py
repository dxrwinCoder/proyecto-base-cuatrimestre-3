import pytest
from models.tarea import Tarea
from services.tarea_service import crear_tarea, actualizar_estado_tarea


@pytest.mark.asyncio
async def test_crear_tarea(db):
    data = {
        "titulo": "Lavar platos",
        "categoria": "cocina",
        "asignado_a": 1,
        "id_hogar": 1,
    }
    tarea = await crear_tarea(db, data)
    assert tarea.id is not None
    assert tarea.titulo == "Lavar platos"
    assert tarea.estado_actual == "pendiente"


@pytest.mark.asyncio
async def test_actualizar_estado_a_completada(db):
    # Crear tarea
    data = {
        "titulo": "Test",
        "categoria": "limpieza",
        "asignado_a": 1,
        "id_hogar": 1,
    }
    tarea = await crear_tarea(db, data)
    assert tarea.estado_actual == "pendiente"

    # Completar tarea
    updated = await actualizar_estado_tarea(db, tarea.id, "completada", miembro_id=1)
    assert updated.estado_actual == "completada"
    assert updated.tiempo_total_segundos is not None

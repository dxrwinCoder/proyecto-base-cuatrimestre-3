import pytest
from datetime import datetime, timedelta, timezone
from services.evento_service import crear_evento, listar_eventos_por_hogar


@pytest.mark.asyncio
async def test_crear_evento(db, setup_rol_hogar):
    data = {
        "titulo": "Reunión",
        "descripcion": "Reunión semanal",
        "fecha_hora": datetime.now(timezone.utc),
        "duracion_min": 30,
        "id_hogar": 1,
        "creado_por": 1,
    }
    # Ajustar: servicio espera dict con datetime, no string
    data["fecha_hora"] = datetime.now(timezone.utc)
    evento = await crear_evento(db, data)
    assert evento.id is not None
    assert evento.titulo == "Reunión"
    assert evento.id_hogar == 1


@pytest.mark.asyncio
async def test_listar_eventos_por_hogar(db, setup_rol_hogar):
    base_time = datetime.now(timezone.utc)
    for i in range(2):
        await crear_evento(
            db,
            {
                "titulo": f"Evento {i}",
                "descripcion": None,
                "fecha_hora": base_time + timedelta(minutes=5 * i),
                "duracion_min": 60,
                "id_hogar": 1,
                "creado_por": 1,
            },
        )

    eventos = await listar_eventos_por_hogar(db, 1)
    assert isinstance(eventos, list)
    assert len(eventos) >= 2

import pytest
from services.modulo_service import crear_modulo


@pytest.mark.asyncio
async def test_crear_modulo(db):
    modulo = await crear_modulo(db, "Miembros", "Gestión de miembros")
    assert modulo.id is not None
    assert modulo.nombre == "Miembros"



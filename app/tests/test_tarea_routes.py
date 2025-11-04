import pytest
from fastapi.testclient import TestClient
from main import app
from models.miembro import Miembro
from utils.security import crear_token_acceso

client = TestClient(app)


# Simula un token JWT válido
def crear_token_test():
    return crear_token_acceso({"sub": "1", "id_hogar": 1})


@pytest.fixture
def setup_miembro(db):
    # Crea un miembro de prueba
    miembro = Miembro(
        id=1,
        nombre_completo="Test User",
        correo_electronico="test@example.com",
        contrasena_hash="fake_hash",
        id_rol=1,
        id_hogar=1,
        estado=True,
    )
    db.add(miembro)
    db.commit()


def test_crear_tarea_sin_autenticacion():
    response = client.post(
        "/tareas/",
        json={"titulo": "Test", "categoria": "cocina", "asignado_a": 1, "id_hogar": 1},
    )
    assert response.status_code == 401


def test_crear_tarea_con_autenticacion(setup_miembro):
    token = crear_token_test()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/tareas/",
        json={
            "titulo": "Lavar platos",
            "categoria": "cocina",
            "asignado_a": 1,
            "id_hogar": 1,
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["titulo"] == "Lavar platos"

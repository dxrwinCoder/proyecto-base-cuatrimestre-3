import pytest
import uuid
from models.miembro import Miembro
from models.rol import Rol
from models.hogar import Hogar
from services.auth_service import (
    autenticar_miembro,
    crear_miembro,
    crear_token_para_miembro,
)
from schemas.auth import MiembroRegistro
from utils.security import obtener_hash_contrasena


@pytest.mark.asyncio
async def test_autenticar_miembro_exitoso(db, setup_rol_hogar):
    """Test para autenticar un miembro con credenciales correctas"""
    # Usar correo único para este test
    correo = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Crear miembro de prueba con contraseña hasheada
    contrasena_plana = "password123"
    contrasena_hash = obtener_hash_contrasena(contrasena_plana)

    miembro = Miembro(
        nombre_completo="Test User",
        correo_electronico=correo,
        contrasena_hash=contrasena_hash,
        id_rol=1,
        id_hogar=1,
        estado=True,
    )
    db.add(miembro)
    # await db.commit()
    await db.flush()

    # Intentar autenticar
    resultado = await autenticar_miembro(db, correo, contrasena_plana)

    assert resultado is not None
    assert resultado.id is not None
    assert resultado.correo_electronico == correo
    assert resultado.nombre_completo == "Test User"


@pytest.mark.asyncio
async def test_autenticar_miembro_credenciales_incorrectas(db, setup_rol_hogar):
    """Test para autenticar un miembro con contraseña incorrecta"""
    # Usar correo único para este test
    correo = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Crear miembro
    contrasena_hash = obtener_hash_contrasena("password123")
    miembro = Miembro(
        nombre_completo="Test User",
        correo_electronico=correo,
        contrasena_hash=contrasena_hash,
        id_rol=1,
        id_hogar=1,
        estado=True,
    )
    db.add(miembro)
    # await db.commit()
    await db.flush()

    # Intentar autenticar con contraseña incorrecta
    resultado = await autenticar_miembro(db, correo, "contraseña_incorrecta")

    assert resultado is None


@pytest.mark.asyncio
async def test_autenticar_miembro_no_existe(db):
    """Test para autenticar un miembro que no existe"""
    resultado = await autenticar_miembro(db, "noexiste@example.com", "password123")

    assert resultado is None


@pytest.mark.asyncio
async def test_crear_miembro_exitoso(db, setup_rol_hogar):
    """Test para crear un nuevo miembro exitosamente"""
    # Usar correo único para este test
    correo = f"nuevo_{uuid.uuid4().hex[:8]}@example.com"

    # Datos de registro
    datos_registro = MiembroRegistro(
        nombre_completo="Nuevo Usuario",
        correo_electronico=correo,
        contrasena="password123",
        id_rol=1,
        id_hogar=1,
    )

    # Crear miembro
    miembro = await crear_miembro(db, datos_registro)

    assert miembro is not None
    assert miembro.id is not None
    assert miembro.nombre_completo == "Nuevo Usuario"
    assert miembro.correo_electronico == correo
    assert miembro.id_rol == 1
    assert miembro.id_hogar == 1
    assert miembro.estado is True


@pytest.mark.asyncio
async def test_crear_miembro_correo_duplicado(db, setup_rol_hogar):
    """Test para intentar crear un miembro con correo ya existente"""

    # Crear primer miembro
    datos_registro1 = MiembroRegistro(
        nombre_completo="Usuario 1",
        correo_electronico="duplicado@example.com",
        contrasena="password123",
        id_rol=1,
        id_hogar=1,
    )
    await crear_miembro(db, datos_registro1)

    # Intentar crear segundo miembro con mismo correo
    datos_registro2 = MiembroRegistro(
        nombre_completo="Usuario 2",
        correo_electronico="duplicado@example.com",
        contrasena="password456",
        id_rol=1,
        id_hogar=1,
    )

    with pytest.raises(ValueError, match="ya se encuentra registrado"):
        await crear_miembro(db, datos_registro2)


@pytest.mark.asyncio
async def test_crear_token_para_miembro(db, setup_rol_hogar):
    """Test para generar token de acceso para un miembro"""
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select

    # Usar correo único para este test
    correo = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Crear miembro
    miembro = Miembro(
        nombre_completo="Test User",
        correo_electronico=correo,
        contrasena_hash=obtener_hash_contrasena("password123"),
        id_rol=1,
        id_hogar=1,
        estado=True,
    )
    db.add(miembro)
    # await db.commit()
    await db.flush()

    # Recargar con rol usando eager loading
    result = await db.execute(
        select(Miembro)
        .options(selectinload(Miembro.rol))
        .where(Miembro.id == miembro.id)
    )
    miembro = result.scalar_one()

    # Generar token
    token = crear_token_para_miembro(miembro)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

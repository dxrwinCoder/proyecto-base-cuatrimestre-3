# tests/test_permiso_service.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.rol import Rol
from models.modulo import Modulo
from models.miembro import Miembro
from models.hogar import Hogar
from schemas.permiso import PermisoCreate, PermisoUpdate
from services.permiso_service import (
    asignar_permiso,
    obtener_permisos_por_rol,
    actualizar_permiso,
    verificar_permiso,
)


@pytest_asyncio.fixture
async def setup_datos_permisos(db: AsyncSession):
    """Crea un Rol, Modulo y Miembro base para los tests"""

    rol_admin = Rol(id=1, nombre="Admin_Test", descripcion="Rol para permisos")
    db.add(rol_admin)

    modulo_test = Modulo(id=1, nombre="TestModulo", descripcion="Módulo para permisos")
    db.add(modulo_test)

    hogar_test = Hogar(id=1, nombre="Hogar_Permiso_Test")
    db.add(hogar_test)

    await db.flush()

    miembro_admin = Miembro(
        id=1,
        nombre_completo="Miembro Permiso Test",
        correo_electronico="permiso@example.com",
        contrasena_hash="123456",
        id_rol=rol_admin.id,
        id_hogar=hogar_test.id,
    )
    db.add(miembro_admin)

    await db.flush()
    await db.refresh(rol_admin)
    await db.refresh(modulo_test)
    await db.refresh(miembro_admin)

    return {"rol": rol_admin, "modulo": modulo_test, "miembro": miembro_admin}


@pytest.mark.asyncio
async def test_asignar_permiso(db: AsyncSession, setup_datos_permisos):
    """Prueba que se puede asignar un permiso nuevo"""
    datos_permiso = PermisoCreate(
        id_rol=setup_datos_permisos["rol"].id,
        id_modulo=setup_datos_permisos["modulo"].id,
        puede_crear=True,
    )

    permiso_creado = await asignar_permiso(db, datos_permiso)

    assert permiso_creado is not None
    assert permiso_creado.id_rol == setup_datos_permisos["rol"].id
    assert permiso_creado.puede_crear is True


@pytest.mark.asyncio
async def test_asignar_permiso_duplicado(db: AsyncSession, setup_datos_permisos):
    """Prueba que falla al asignar un permiso duplicado (mismo rol/módulo)"""
    datos_permiso = PermisoCreate(
        id_rol=setup_datos_permisos["rol"].id,
        id_modulo=setup_datos_permisos["modulo"].id,
        puede_crear=True,
    )
    await asignar_permiso(db, datos_permiso)  # Asignamos el primero

    # Intentamos asignar otro al mismo rol/módulo
    datos_permiso_2 = PermisoCreate(
        id_rol=setup_datos_permisos["rol"].id,
        id_modulo=setup_datos_permisos["modulo"].id,
        puede_leer=True,
    )

    with pytest.raises(ValueError, match="Este permiso ya existe"):
        await asignar_permiso(db, datos_permiso_2)


@pytest.mark.asyncio
async def test_verificar_permiso_exitoso_y_fallido(
    db: AsyncSession, setup_datos_permisos
):
    """Prueba que la verificación de permiso 'True' y 'False' funciona"""
    datos_permiso = PermisoCreate(
        id_rol=setup_datos_permisos["rol"].id,
        id_modulo=setup_datos_permisos["modulo"].id,
        puede_eliminar=True,  # Damos permiso
        puede_crear=False,  # Explícitamente NO damos permiso
    )
    await asignar_permiso(db, datos_permiso)

    miembro_id = setup_datos_permisos["miembro"].id

    # 1. Prueba 'True' (puede_eliminar)
    tiene_permiso_eliminar = await verificar_permiso(
        db, id_miembro=miembro_id, modulo_nombre="TestModulo", accion="eliminar"
    )
    assert tiene_permiso_eliminar is True

    # 2. Prueba 'False' (puede_crear)
    tiene_permiso_crear = await verificar_permiso(
        db, id_miembro=miembro_id, modulo_nombre="TestModulo", accion="crear"
    )
    assert tiene_permiso_crear is False

    # 3. Prueba 'False' por default (puede_actualizar)
    tiene_permiso_actualizar = await verificar_permiso(
        db, id_miembro=miembro_id, modulo_nombre="TestModulo", accion="actualizar"
    )
    assert tiene_permiso_actualizar is False

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from db.database import Base  # ¡Importante! Asegúrese que Base esté importado
from models.rol import Rol
from models.hogar import Hogar

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# --- ¡ESTA ES LA FIXTURE MODIFICADA! ---
@pytest_asyncio.fixture(scope="function")
async def db():
    """
    Fixture de base de datos que garantiza aislamiento total:
    1. Crea todas las tablas.
    2. Inicia una sesión.
    3. Entrega la sesión al test.
    4. Cierra la sesión y borra todas las tablas.
    """
    async with engine.begin() as conn:
        # 1. Crear todas las tablas
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        try:
            # 2. Entregar la sesión
            yield session
        finally:
            # 3. Limpieza
            await session.rollback()  # Rollback por si algo quedó pendiente
            await session.close()

    async with engine.begin() as conn:
        # 4. Borrar todo para el siguiente test
        await conn.run_sync(Base.metadata.drop_all)


# --- FIN DE LA MODIFICACIÓN ---


@pytest_asyncio.fixture(scope="function")
async def setup_rol_hogar(db: AsyncSession):  # ¡Recibe la nueva fixture 'db'!
    """Fixture compartida para crear Rol y Hogar base en cada test"""
    from sqlalchemy import select

    # Verificar si ya existen
    rol_result = await db.execute(select(Rol).where(Rol.id == 1))
    rol = rol_result.scalar_one_or_none()

    if not rol:
        rol = Rol(id=1, nombre="Usuario", descripcion="Rol de usuario", estado=True)
        db.add(rol)

    hogar_result = await db.execute(select(Hogar).where(Hogar.id == 1))
    hogar = hogar_result.scalar_one_or_none()

    if not hogar:
        hogar = Hogar(id=1, nombre="Hogar Test", estado=True)
        db.add(hogar)

    # --- ¡CAMBIO CLAVE! ---
    # ¡NO MÁS COMMIT! Usamos FLUSH para que los datos existan DENTRO de la transacción
    await db.flush()

    # Refresh para que los objetos tengan los datos de la BD (como IDs)
    await db.refresh(rol)
    await db.refresh(hogar)

    return {"rol": rol, "hogar": hogar}


# -----------------------------------------------------------------------------------------------------
# # tests/conftest.py generado por cursor
# import pytest
# import pytest_asyncio
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import StaticPool
# from db.database import Base
# from models.rol import Rol
# from models.hogar import Hogar

# DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# engine = create_async_engine(
#     DATABASE_URL,
#     connect_args={"check_same_thread": False},
#     poolclass=StaticPool,
# )
# TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# @pytest_asyncio.fixture(scope="function")
# async def db():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     async with TestingSessionLocal() as session:
#         yield session
#         await session.rollback()


# @pytest_asyncio.fixture(scope="function")
# async def setup_rol_hogar(db):
#     """Fixture compartida para crear Rol y Hogar base en cada test"""
#     from sqlalchemy import select

#     # Verificar si ya existen
#     rol_result = await db.execute(select(Rol).where(Rol.id == 1))
#     rol = rol_result.scalar_one_or_none()

#     if not rol:
#         rol = Rol(id=1, nombre="Usuario", descripcion="Rol de usuario", estado=True)
#         db.add(rol)

#     hogar_result = await db.execute(select(Hogar).where(Hogar.id == 1))
#     hogar = hogar_result.scalar_one_or_none()

#     if not hogar:
#         hogar = Hogar(id=1, nombre="Hogar Test", estado=True)
#         db.add(hogar)

#     await db.commit()
#     await db.refresh(rol)
#     await db.refresh(hogar)

#     return {"rol": rol, "hogar": hogar}

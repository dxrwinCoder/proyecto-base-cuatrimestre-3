
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base  # ← Añadido declarative_base
from config.config import settings

# Motor asíncrono
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Sesión asíncrona
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


Base = declarative_base()

# Dependencia para FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
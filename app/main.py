from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine, Base
from sqlalchemy.ext.asyncio import AsyncEngine
from models.hogar import Hogar
from models.rol import Rol
from models.modulo import Modulo
from models.permiso import Permiso
from models.miembro import Miembro
from models.tarea import Tarea
from models.mensaje import Mensaje
from models.evento import Evento

from utils.logger import setup_logger

logger = setup_logger("main")
from routes import  permiso_routes,tarea_routes, mensaje_routes, auth_routes, hogar_routes,evento_routes, modulo_routes

app = FastAPI(title="HomeTasks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas
app.include_router(permiso_routes.router)
app.include_router(tarea_routes.router)
app.include_router(mensaje_routes.router)
app.include_router(auth_routes.router)
app.include_router(hogar_routes.router)
app.include_router(evento_routes.router)
app.include_router(modulo_routes.router)


@app.on_event("startup")
async def startup():
    try:
        logger.info("Iniciando la aplicación...")
        # Crea todas las tablas en la base de datos
        async with engine.begin() as conn:
            logger.info("Creando tablas en la base de datos...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tablas creadas exitosamente")
    except Exception as e:
        logger.error(f"Error durante el inicio de la aplicación: {str(e)}")
        raise

@app.get("/")
async def root():
    try:
        logger.info("Acceso a la ruta raíz de la API")
        return {"mensaje": "Bienvenido a HomeTasks API"}
    except Exception as e:
        logger.error(f"Error en la ruta raíz: {str(e)}")
        raise
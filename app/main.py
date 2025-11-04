from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# from fastapi.security import OAuth2PasswordBearer
from db.database import engine, Base
from contextlib import asynccontextmanager

# from sqlalchemy.ext.asyncio import AsyncEngine
# from models.hogar import Hogar
# from models.rol import Rol
# from models.modulo import Modulo
# from models.permiso import Permiso
# from models.miembro import Miembro
# from models.tarea import Tarea
# from models.mensaje import Mensaje
# from models.evento import Evento
from routes import (
    permiso_routes,
    tarea_routes,
    mensaje_routes,
    auth_routes,
    hogar_routes,
    evento_routes,
    modulo_routes,
    miembro_routes,
)

from utils.logger import setup_logger

logger = setup_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Iniciar la app
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="HomeTasks API",
    description="API para gestión de tareas del hogar",
    version="1.0.0",
    lifespan=lifespan,
    # Esto le dice a Swagger qué ruta usar para el botón "Authorize"
    # swagger_ui_init_oauth={"usePkceWithAuthorizationCodeGrant": False},
)

# Configura el esquema de seguridad para Swagger
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login-swagger")


# Middleware para redirigir /auth/login → /auth/login-swagger
# @app.middleware("http")
# async def redirect_login(request: Request, call_next):
#     if request.url.path == "/auth/login" and request.method == "POST":
#         # Cambiamos la URL temporalmente
#         request.scope["path"] = "/auth/login-swagger"
#     response = await call_next(request)
#     return response


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
app.include_router(miembro_routes.router)


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

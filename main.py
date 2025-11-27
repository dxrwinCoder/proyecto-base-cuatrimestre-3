from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket

# from fastapi.security import OAuth2PasswordBearer
from db.database import engine, Base
from contextlib import asynccontextmanager

from routes import (
    permiso_routes,
    tarea_routes,
    mensaje_routes,
    auth_routes,
    hogar_routes,
    evento_routes,
    modulo_routes,
    atributo_routes,
    miembro_routes,
    notificacion_routes,
    assistant_routes,
    assistant_ai_routes,
    asistente_service_routes,
    comentario_tarea_routes,
)
from notificaciones_cloud_api.router import router as whatsapp_cloud_router
from websocket.chat import chat_websocket

from utils.logger import setup_logger

logger = setup_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Iniciar la app
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

    yield

    # Shutdown: Código de limpieza (si es necesario)
    logger.info("Cerrando la aplicación...")


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
app.include_router(atributo_routes.router)
app.include_router(miembro_routes.router)
app.include_router(notificacion_routes.router)
app.include_router(assistant_routes.router)
app.include_router(assistant_ai_routes.router)
app.include_router(asistente_service_routes.router)
app.include_router(comentario_tarea_routes.router)
app.include_router(whatsapp_cloud_router)


@app.get("/")
async def root():
    try:
        logger.info("Acceso a la ruta raíz de la API")
        return {"mensaje": "Bienvenido a HomeTasks API"}
    except Exception as e:
        logger.error(f"Error en la ruta raíz: {str(e)}")
        raise


@app.websocket("/ws/chat/{destinatario_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket, destinatario_id: int, token: str
):
    # token debe venir como query param ?token=...
    await chat_websocket(websocket, token, destinatario_id)

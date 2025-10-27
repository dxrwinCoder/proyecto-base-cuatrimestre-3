from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
    DEBUG: bool = os.getenv("DEBUG")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT")


settings = Settings()

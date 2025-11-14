import logging
import sys
from logging.handlers import RotatingFileHandler
import os

# Configurar el directorio de logs
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)


# Configurar el logger
def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Cambiar a DEBUG para capturar más detalles

    # Crear formateador más detallado
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configurar handler para archivo
    file_handler = RotatingFileHandler(
        os.path.join(log_directory, f"{name}.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Configurar handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Mantener INFO en consola para no saturar
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

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
    logger.setLevel(logging.INFO)

    # Crear formateador
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configurar handler para archivo
    file_handler = RotatingFileHandler(
        os.path.join(log_directory, f"{name}.log"),
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Configurar handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
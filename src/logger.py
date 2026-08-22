"""
Configuracion de los logs del proyecto.

Regla del equipo: en src/ no se usa print(). Todo mensaje pasa por aqui.

Los logs nos sirven para tres cosas de la rubrica:
  - dejar constancia de cual regla de calidad fallo y con que valor
  - registrar los incidentes del batch contaminado (detecta -> avisa -> registra)
  - medir latencia y errores de la API para el system monitoring

Uso en cualquier modulo:

    from src.logger import get_logger
    log = get_logger(__name__)
    log.info("mensaje")
"""

import logging
import sys

from src.config import LOGS_DIR

FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FECHA = "%Y-%m-%d %H:%M:%S"

_configurado = False


def _configurar():
    """Prepara el logger raiz una sola vez por ejecucion."""
    global _configurado
    if _configurado:
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(FORMATO, datefmt=FECHA)

    # A consola, para ver que pasa mientras corre
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formatter)

    # A archivo, para poder revisarlo despues
    archivo = logging.FileHandler(LOGS_DIR / "pipeline.log", encoding="utf-8")
    archivo.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(consola)
    root.addHandler(archivo)

    _configurado = True


def get_logger(nombre):
    """Devuelve el logger del modulo que lo pide."""
    _configurar()
    return logging.getLogger(nombre)

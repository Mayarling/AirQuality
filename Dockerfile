# Imagen del servicio de pronostico de benceno.
# Grupo 8 - Mayarling Martinez y Nicole Chavarria
#
# Se construye y se levanta asi:
#
#   docker build -t grupo8-mlops .
#   docker run -p 8000:8000 grupo8-mlops
#
# Antes de construir hay que haber entrenado, porque la imagen copia
# models/produccion, que es lo que produce el entrenamiento.

# Version fija, no "latest". Con "latest" la imagen cambiaria sola de un dia
# para otro y dejaria de ser reproducible, que es justo lo que no queremos.
FROM python:3.12-slim

# --- Ajustes de Python ---------------------------------------------------
# PYTHONDONTWRITEBYTECODE: no genera archivos .pyc, que solo ocupan espacio
# PYTHONUNBUFFERED: los logs salen al momento y no se quedan en el buffer, que
#   es lo que hace que "docker logs" se vea vacio cuando algo falla
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# --- Dependencias --------------------------------------------------------
# Se copia solo el archivo de requisitos antes que el codigo. Docker guarda en
# cache cada paso: si despues cambiamos una linea del codigo, no vuelve a
# instalar las librerias. Al reves tardaria varios minutos en cada cambio.
#
# Se instala requirements-api.txt y no requirements.txt: la API no necesita
# MLflow, matplotlib ni statsmodels. Medido: la imagen pasa de 1.33 GB a
# 865 MB, cerca de un 35% menos.
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# --- Codigo y modelo -----------------------------------------------------
COPY src/ ./src/
COPY models/ ./models/

# --- Usuario sin privilegios ---------------------------------------------
# Por defecto el contenedor corre como root. Si alguien lograra entrar por la
# API, tendria permisos de administrador adentro. Con un usuario normal, no.
RUN useradd --create-home --shell /bin/bash servicio \
    && mkdir -p /app/logs \
    && chown -R servicio:servicio /app
USER servicio

EXPOSE 8000

# --- Chequeo de salud ----------------------------------------------------
# Docker le pega a /health cada 30 segundos. Si deja de responder, marca el
# contenedor como unhealthy y se ve en "docker ps".
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

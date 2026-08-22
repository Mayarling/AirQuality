"""
Configuracion central del proyecto.

Todo lo que sea una ruta, un umbral o una fecha de corte vive aqui.
Si hay que cambiar algo, se cambia en este archivo y no en cinco lugares distintos.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
# parents[1] sube desde src/config.py hasta la raiz del repositorio
BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

RAW_FILE = RAW_DIR / "AirQualityUCI.csv"
INTERIM_FILE = INTERIM_DIR / "air_quality_interim.parquet"

# --------------------------------------------------------------------------
# Fuente de los datos
# --------------------------------------------------------------------------
DATASET_NAME = "Air Quality (UCI, id 360)"
DATASET_URL = "https://archive.ics.uci.edu/static/public/360/air+quality.zip"
DATASET_PAGE = "https://archive.ics.uci.edu/dataset/360/air+quality"
DATASET_DOI = "10.24432/C59K5F"
# Nombre del csv que viene adentro del zip
FILE_IN_ZIP = "AirQualityUCI.csv"

# El csv de UCI usa punto y coma como separador y coma como decimal.
CSV_SEP = ";"
CSV_DECIMAL = ","

# --------------------------------------------------------------------------
# Esquema esperado
# --------------------------------------------------------------------------
# Nombres exactos como vienen en el archivo original. Los puntos y parentesis
# son parte del nombre, no se pueden cambiar al leer.
EXPECTED_COLUMNS = [
    "Date",
    "Time",
    "CO(GT)",
    "PT08.S1(CO)",
    "NMHC(GT)",
    "C6H6(GT)",
    "PT08.S2(NMHC)",
    "NOx(GT)",
    "PT08.S3(NOx)",
    "NO2(GT)",
    "PT08.S4(NO2)",
    "PT08.S5(O3)",
    "T",
    "RH",
    "AH",
]

# Columnas numericas (todas menos Date y Time)
NUMERIC_COLUMNS = EXPECTED_COLUMNS[2:]

# Codigo con el que UCI marca los datos faltantes
MISSING_CODE = -200

# Filas que trae el archivo original despues de quitar las lineas vacias.
# Sirve como control: si la ingesta devuelve otra cosa, algo cambio.
EXPECTED_ROWS = 9357

# --------------------------------------------------------------------------
# Problema
# --------------------------------------------------------------------------
# Variable a pronosticar. Se escogio C6H6(GT) porque solo tiene 3.91% de
# faltantes y es una concentracion real, no una lectura cruda de sensor.
TARGET = "C6H6(GT)"

# Cuantas horas hacia adelante queremos pronosticar
FORECAST_HORIZON = 24

# Columna que descartamos: 90.23% de sus valores son -200, rellenarla seria
# inventar datos.
COLUMNS_TO_DROP = ["NMHC(GT)"]

RANDOM_SEED = 42

# --------------------------------------------------------------------------
# Cortes temporales
# --------------------------------------------------------------------------
# El dataset va del 2004-03-10 18:00 al 2005-04-04 14:00 (9357 horas seguidas,
# sin huecos). Es una serie de tiempo, asi que los cortes son por fecha y nunca
# al azar.
#
#   REFERENCE  = TRAIN + VALIDATION  -> lo que el modelo conoce
#   BATCH 1/2/3                      -> "produccion", llega despues en el tiempo
#
# Las fechas son el inicio de cada tramo. El tramo termina donde empieza el
# siguiente.
SPLIT_TRAIN_START = "2004-03-10"
SPLIT_VALID_START = "2004-08-16"
SPLIT_BATCH1_START = "2004-10-01"
SPLIT_BATCH2_START = "2004-12-01"
SPLIT_BATCH3_START = "2005-02-01"

# --------------------------------------------------------------------------
# Umbrales de las reglas de calidad
# --------------------------------------------------------------------------
MIN_ROWS = 8000  # si llegan menos filas que esto, algo se rompio en la ingesta
MAX_DUPLICATE_RATE = 0.01  # como maximo 1% de filas repetidas
MAX_MISSING_RATE_TARGET = 0.10  # el target no puede pasar de 10% de huecos

# Rangos fisicos posibles. Un valor fuera de aqui no es un outlier, es un error.
# T y RH salen del propio dataset (norte de Italia); el resto no puede ser
# negativo despues de convertir los -200 a nulo.
VALID_RANGES = {
    "T": (-20.0, 55.0),
    "RH": (0.0, 100.0),
    "AH": (0.0, 3.0),
    "CO(GT)": (0.0, 100.0),
    "C6H6(GT)": (0.0, 100.0),
    "NOx(GT)": (0.0, 2000.0),
    "NO2(GT)": (0.0, 1000.0),
}

# --------------------------------------------------------------------------
# Umbrales de drift (se justifican en el informe, no son leyes universales)
# --------------------------------------------------------------------------
PSI_WARNING = 0.10
PSI_ALERT = 0.25

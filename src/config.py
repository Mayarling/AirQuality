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
PROCESSED_FILE = PROCESSED_DIR / "air_quality_limpio.parquet"
FEATURES_FILE = PROCESSED_DIR / "features.parquet"
REPORTE_CALIDAD = REPORTS_DIR / "diagnostico_calidad.md"

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

# El arreglo de sensores de estado solido y las variables ambientales que lo
# acompañan. Todas estas se apagan juntas cuando el equipo deja de medir.
# C6H6(GT) va en este grupo porque su valor se deriva de PT08.S2(NMHC).
SENSOR_COLUMNS = [
    "PT08.S1(CO)",
    "PT08.S2(NMHC)",
    "PT08.S3(NOx)",
    "PT08.S4(NO2)",
    "PT08.S5(O3)",
    "C6H6(GT)",
    "T",
    "RH",
    "AH",
]

# Mediciones del analizador certificado de referencia. Es un instrumento
# distinto del arreglo de sensores, por eso falla en otros momentos.
REFERENCE_COLUMNS = ["CO(GT)", "NMHC(GT)", "NOx(GT)", "NO2(GT)"]

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

# Los faltantes no estan sueltos: son 16 apagones del equipo, el mas largo de
# 76 horas seguidas. Solo rellenamos los huecos cortos; un hueco de tres dias
# no se inventa.
MAX_GAP_INTERPOLAR = 3  # horas

# El benceno tiene sesgo 1.362 (cola larga de picos). Con logaritmo baja a
# -0.233. Modelamos en log y devolvemos las metricas en la escala original.
USAR_LOG_TARGET = True

RANDOM_SEED = 42

# --------------------------------------------------------------------------
# Variables del modelo (salieron del analisis exploratorio)
# --------------------------------------------------------------------------
# Los rezagos estan medidos DESDE LA HORA QUE QUEREMOS PREDECIR, no desde
# ahora. Por eso ninguno puede ser menor que FORECAST_HORIZON: a la hora t no
# conocemos nada de lo que pasa entre t+1 y t+23.
#
# El 24 y el 168 los escogio la autocorrelacion (0.656 y 0.592). El 25 y el 48
# acompañan para darle contexto al modelo.
LAGS_TARGET = [24, 25, 48, 168]

# Ventanas de media movil, en horas, calculadas hasta el momento de predecir.
VENTANAS_MOVILES = [3, 24]

# Sensores que entran como variable, siempre rezagados. PT08.S2 es el que
# correlaciona 0.982 con el benceno: justamente por eso solo puede entrar
# rezagado y nunca del mismo instante que queremos predecir.
SENSORES_FEATURE = ["PT08.S1(CO)", "PT08.S2(NMHC)", "PT08.S5(O3)"]

# Variables ambientales que tambien entran rezagadas.
AMBIENTALES_FEATURE = ["T", "RH", "AH"]

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

# --------------------------------------------------------------------------
# MLflow
# --------------------------------------------------------------------------
# Guardamos todo en la carpeta mlruns del proyecto. No se sube a Git: se
# regenera corriendo el entrenamiento.
MLFLOW_TRACKING_URI = f"file:///{(BASE_DIR / 'mlruns').as_posix()}"
MLFLOW_EXPERIMENT = "air-quality-benceno-24h"

# Nombre con el que queda el modelo en el Model Registry
MODELO_REGISTRADO = "grupo8-benceno-24h"

# Alias que representan el ciclo del enunciado:
#   Experiment -> Candidate -> Validation -> Production
# En MLflow los stages quedaron obsoletos; los alias hacen lo mismo y se ven
# igual de claro en la interfaz.
ALIAS_CANDIDATO = "candidato"
ALIAS_PRODUCCION = "produccion"

# --------------------------------------------------------------------------
# Criterios explicitos para escoger el modelo (seccion J)
# --------------------------------------------------------------------------
# No se escoge "el que dio mejor". Un modelo tiene que cumplir las tres
# condiciones para siquiera ser candidato, y entre los que cumplen gana el de
# menor MAE en validacion.
#
# 1. Ganarle al baseline por un margen que valga la pena. Si un modelo
#    complicado apenas empata con repetir el valor de ayer, no compensa
#    mantenerlo en produccion.
MEJORA_MINIMA_VS_BASELINE = 0.10   # 10% menos de MAE

# 2. No estar sobreajustado. Si el error en validacion es mucho peor que en
#    entrenamiento, el modelo se aprendio el ruido.
MAX_DEGRADACION_TRAIN_VALID = 0.60  # el MAE de validacion no puede ser 60% peor

# 3. Un techo de error absoluto, para que el pronostico sirva de algo.
MAE_MAXIMO_ACEPTABLE = 5.0          # ug/m3

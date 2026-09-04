"""
Ingesta del dataset Air Quality de UCI.

Descarga el zip desde la fuente oficial, saca el csv y lo guarda en data/raw
sin modificarle nada. Ese archivo es la capa RAW y no se vuelve a tocar.

Despues arma la capa INTERIM: convierte los -200 en nulos, junta Date y Time en
un solo timestamp y lo guarda en parquet.

Se ejecuta asi:

    python -m src.ingestion.ingest

Opciones:

    --force     vuelve a descargar aunque el archivo ya exista
    --offline   no intenta descargar, usa el archivo que ya esta en data/raw
"""

import argparse
import hashlib
import io
import sys
import zipfile

import pandas as pd
import requests

from src import config
from src.logger import get_logger

log = get_logger(__name__)

TIMEOUT = 60


def descargar_zip(url):
    """Baja el zip de UCI y devuelve el contenido en memoria."""
    log.info("Descargando desde %s", url)
    respuesta = requests.get(url, timeout=TIMEOUT)
    respuesta.raise_for_status()
    log.info("Descarga completa: %.1f KB", len(respuesta.content) / 1024)
    return respuesta.content


def extraer_csv(contenido_zip, nombre_archivo, destino):
    """Saca el csv de adentro del zip y lo escribe tal cual en destino."""
    with zipfile.ZipFile(io.BytesIO(contenido_zip)) as z:
        adentro = z.namelist()
        log.info("El zip contiene: %s", adentro)

        if nombre_archivo not in adentro:
            raise FileNotFoundError(
                f"No encontre {nombre_archivo} dentro del zip. Hay: {adentro}"
            )

        destino.parent.mkdir(parents=True, exist_ok=True)
        with z.open(nombre_archivo) as origen, open(destino, "wb") as salida:
            salida.write(origen.read())

    log.info("Guardado en %s", destino)


def hash_archivo(ruta):
    """
    Huella md5 del archivo crudo. La usamos como data_version en MLflow para
    poder responder con que datos exactos se entreno cada modelo.
    """
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_raw(ruta):
    """
    Lee el csv crudo.

    Este archivo tiene tres mañas que hay que atender de una vez:
      - el separador es punto y coma, no coma
      - los decimales vienen con coma (2,6 en vez de 2.6)
      - trae dos columnas vacias al final y varias filas vacias abajo
    """
    df = pd.read_csv(ruta, sep=config.CSV_SEP, decimal=config.CSV_DECIMAL)
    log.info("Archivo crudo leido: %s filas x %s columnas", *df.shape)

    antes = df.shape
    df = df.dropna(how="all", axis=1)  # fuera las columnas vacias
    df = df.dropna(how="all", axis=0)  # fuera las filas vacias del final
    log.info("Despues de quitar filas y columnas vacias: %s -> %s", antes, df.shape)

    return df


def verificar_esquema(df):
    """Revisa que esten todas las columnas esperadas y en el orden esperado."""
    columnas = list(df.columns)

    faltan = [c for c in config.EXPECTED_COLUMNS if c not in columnas]
    sobran = [c for c in columnas if c not in config.EXPECTED_COLUMNS]

    if faltan:
        raise ValueError(f"Faltan columnas en el archivo: {faltan}")
    if sobran:
        log.warning("Aparecieron columnas que no esperaba: %s", sobran)

    if len(df) != config.EXPECTED_ROWS:
        log.warning(
            "Esperaba %s filas y llegaron %s. Revisar si la fuente cambio.",
            config.EXPECTED_ROWS,
            len(df),
        )
    else:
        log.info("Conteo de filas correcto: %s", len(df))


def armar_timestamp(df):
    """
    Junta Date y Time en una sola columna de fecha y hora.

    Date viene como 10/03/2004 (dia/mes/año) y Time como 18.00.00, con puntos
    en vez de dos puntos. Hay que arreglar el Time antes de convertir.
    """
    hora = df["Time"].astype(str).str.replace(".", ":", regex=False)
    df["datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + hora,
        format="%d/%m/%Y %H:%M:%S",
    )
    df = df.drop(columns=["Date", "Time"])

    # La columna de fecha va de primera, se lee mejor
    columnas = ["datetime"] + [c for c in df.columns if c != "datetime"]
    df = df[columnas].sort_values("datetime").reset_index(drop=True)

    log.info(
        "Rango temporal: %s a %s",
        df["datetime"].min(),
        df["datetime"].max(),
    )
    return df


def marcar_faltantes(df):
    """
    Convierte los -200 en nulos.

    Esto tiene que pasar antes de calcular cualquier promedio o correlacion.
    Si se deja el -200 como numero, pandas lo trata como una medicion real y
    arruina toda la estadistica.
    """
    total = 0
    for columna in config.NUMERIC_COLUMNS:
        if columna not in df.columns:
            continue
        marcadas = (df[columna] == config.MISSING_CODE).sum()
        if marcadas:
            df.loc[df[columna] == config.MISSING_CODE, columna] = pd.NA
            total += marcadas
            log.info(
                "  %-16s %5d faltantes (%5.2f%%)",
                columna,
                marcadas,
                marcadas / len(df) * 100,
            )

    df[config.NUMERIC_COLUMNS] = df[config.NUMERIC_COLUMNS].astype("float64")
    log.info("Total de valores convertidos de -200 a nulo: %s", total)
    return df


def revisar_continuidad(df):
    """Cuenta cuantas horas faltan en la serie y si hay timestamps repetidos."""
    fechas = df["datetime"]

    repetidos = int(fechas.duplicated().sum())
    if repetidos:
        log.error("Hay %s timestamps repetidos", repetidos)
    else:
        log.info("Sin timestamps repetidos")

    completo = pd.date_range(fechas.min(), fechas.max(), freq="h")
    huecos = len(completo) - len(fechas)
    if huecos:
        log.warning("Faltan %s horas en la serie", huecos)
    else:
        log.info("Serie horaria completa: %s horas seguidas", len(fechas))

    return huecos


def main():
    parser = argparse.ArgumentParser(description="Ingesta del dataset Air Quality")
    parser.add_argument("--force", action="store_true", help="vuelve a descargar")
    parser.add_argument("--offline", action="store_true", help="no descarga nada")
    args = parser.parse_args()

    log.info("=" * 62)
    log.info("INGESTA - %s", config.DATASET_NAME)
    log.info("=" * 62)

    # --- capa RAW ---
    if config.RAW_FILE.exists() and not args.force:
        log.info("Ya existe %s, no lo vuelvo a bajar (usar --force)", config.RAW_FILE)
    elif args.offline:
        log.error("Modo offline y no hay archivo en %s", config.RAW_FILE)
        return 1
    else:
        try:
            contenido = descargar_zip(config.DATASET_URL)
            extraer_csv(contenido, config.FILE_IN_ZIP, config.RAW_FILE)
        except Exception as e:
            log.error("Fallo la descarga: %s", e)
            # Respaldo: si ya teniamos una copia de una corrida anterior,
            # seguimos con ella. Sirve para que la demo no dependa de que el
            # sitio de UCI este arriba ese dia.
            if config.RAW_FILE.exists():
                log.warning("Sigo con la copia local que ya estaba en data/raw")
            else:
                log.error("Bajalo a mano de %s y ponelo en %s",
                          config.DATASET_PAGE, config.RAW_FILE)
                return 1

    version = hash_archivo(config.RAW_FILE)
    log.info("data_version (md5): %s", version)

    # --- capa INTERIM ---
    df = cargar_raw(config.RAW_FILE)
    verificar_esquema(df)
    df = armar_timestamp(df)

    log.info("Convirtiendo los %s a nulo:", config.MISSING_CODE)
    df = marcar_faltantes(df)

    revisar_continuidad(df)

    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.INTERIM_FILE, index=False)
    log.info("Capa interim guardada en %s (%s filas)", config.INTERIM_FILE, len(df))

    log.info("Ingesta terminada sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())

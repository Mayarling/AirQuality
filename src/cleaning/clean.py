"""
Limpieza de los datos, con las decisiones del diagnóstico ya tomadas.

Toma la capa interim y produce la capa processed. Las tres decisiones y su
razon:

1. Se elimina NMHC(GT).
   Tiene 90.23% de huecos (8443 de 9357 filas). Rellenar eso no seria imputar,
   seria inventar la columna entera.

2. Se rellenan por interpolacion solo los huecos de hasta 3 horas seguidas.
   Los huecos no están sueltos: son 16 apagones del equipo, el más largo de 76
   horas. Un hueco de tres días no se estima con la media ni con el vecino.
   Las filas de los huecos largos se quedan como nulo, a la vista.

3. NO se borran filas.
   La serie tiene que seguir siendo horaria y sin saltos para poder calcular
   los lags más adelante. Si borraramos filas, el lag de 24 horas dejaria de
   apuntar 24 horas atras. Las filas sin target se filtran despues, al entrenar.

Ademas se agrega la columna `imputado`, que marca con True las filas donde el
target fue rellenado. Sirve para poder excluirlas si alguna vez queremos medir
solo contra mediciones reales.

Se ejecuta asi:

    python -m src.cleaning.clean
"""

import sys

import pandas as pd

from src import config
from src.logger import get_logger
from src.validation.quality_gates import correr_gates

log = get_logger(__name__)


def interpolar_huecos_cortos(serie, max_horas):
    """
    Rellena por interpolacion solo las rachas de nulos de hasta max_horas.

    Ojo con la diferencia: pandas tiene el parametro limit=3, pero ese rellena
    las 3 primeras horas de un hueco de 76, que es justo lo que no queremos.
    Aquí primero se mide cuanto dura cada racha completa y solo se tocan las
    que caben enteras dentro del limite.
    """
    nulo = serie.isna()
    if not nulo.any():
        return serie.copy(), nulo & False

    racha = (nulo != nulo.shift()).cumsum()
    largo = nulo.groupby(racha).transform("sum")
    rellenable = nulo & (largo <= max_horas)

    # limit_area="inside" evita inventar valores antes del primer dato o
    # despues del ultimo.
    interpolada = serie.interpolate(method="time", limit_area="inside")

    salida = serie.copy()
    salida[rellenable] = interpolada[rellenable]
    return salida, rellenable


def main():
    log.info("=" * 62)
    log.info("LIMPIEZA")
    log.info("=" * 62)

    if not config.INTERIM_FILE.exists():
        log.error("No existe %s. Corra primero la ingesta.", config.INTERIM_FILE)
        return 1

    df = pd.read_parquet(config.INTERIM_FILE)
    log.info("Entrada: %s filas x %s columnas", *df.shape)

    # Gate de entrada. Si algo grave viene mal, mejor parar aquí que descubrirlo
    # despues de entrenar.
    correr_gates(df, etapa="entrada", detener=True)

    # --- Decision 1: eliminar columnas inservibles ------------------------
    for columna in config.COLUMNS_TO_DROP:
        if columna in df.columns:
            pct = df[columna].isna().mean() * 100
            df = df.drop(columns=[columna])
            log.info("Eliminada la columna %s (tenia %.2f%% de huecos)", columna, pct)

    # La interpolacion por tiempo necesita que la fecha sea el indice
    df = df.set_index("datetime").sort_index()

    # --- Decision 2: interpolar solo huecos cortos ------------------------
    log.info("Interpolando huecos de hasta %s horas seguidas:", config.MAX_GAP_INTERPOLAR)

    imputado_target = None
    total_rellenado = 0

    for columna in df.columns:
        antes = int(df[columna].isna().sum())
        if antes == 0:
            continue

        df[columna], rellenable = interpolar_huecos_cortos(
            df[columna], config.MAX_GAP_INTERPOLAR
        )
        rellenados = int(rellenable.sum())
        despues = int(df[columna].isna().sum())
        total_rellenado += rellenados

        log.info("  %-16s %4d nulos -> rellenados %3d -> quedan %4d",
                 columna, antes, rellenados, despues)

        if columna == config.TARGET:
            imputado_target = rellenable

    log.info("Total de valores rellenados: %s", total_rellenado)

    # --- Decision 3: no borrar filas, solo marcar -------------------------
    df["imputado"] = imputado_target if imputado_target is not None else False
    df = df.reset_index()

    sin_target = int(df[config.TARGET].isna().sum())
    log.info("Filas sin target despues de limpiar: %s de %s (%.2f%%)",
             sin_target, len(df), sin_target / len(df) * 100)
    log.info("Las filas se conservan para no romper la continuidad horaria. "
             "Se filtran al entrenar.")

    # --- Guardar ----------------------------------------------------------
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.PROCESSED_FILE, index=False)
    log.info("Capa processed guardada en %s (%s filas x %s columnas)",
             config.PROCESSED_FILE, *df.shape)

    # Gate de salida sobre las filas que si tienen target: son las que van a
    # entrenar y esas ya no pueden tener huecos.
    entrenables = df[df[config.TARGET].notna()].copy()
    log.info("Verificando las %s filas entrenables:", len(entrenables))
    correr_gates(entrenables, etapa="salida", detener=True)

    log.info("Limpieza terminada sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())

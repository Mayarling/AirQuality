"""
Construccion de las variables del modelo.

Este archivo es el unico lugar donde se arman las variables. Lo llama el
entrenamiento y lo llama la API. La seccion H del enunciado prohibe tener una
logica de features en el notebook y otra distinta en produccion, y la forma de
cumplirlo es que las dos partes llamen a la misma funcion.

Como se plantea el problema
---------------------------
Estamos parados en la hora t y queremos saber cuanto benceno va a haber en la
hora t+24.

Todos los rezagos estan medidos **desde la hora que queremos predecir**, no
desde ahora. Es decir, "rezago 24" significa el valor de 24 horas antes del
momento objetivo, que es justamente el valor de ahora.

De ahi sale la regla que nos protege del leakage:

    ningun rezago puede ser menor que el horizonte

Si alguien pide un rezago de 3 horas con un horizonte de 24, la funcion lanza
un error en vez de devolver un modelo que parece buenisimo y es mentira. Esa
comprobacion esta en `_validar_rezago` y hay una prueba que la verifica.

La unica excepcion son las variables de calendario. La hora del dia y el dia de
la semana del momento objetivo **si** se conocen por adelantado: hoy a las 3 de
la tarde ya sabemos que dentro de 24 horas van a ser las 3 de la tarde del dia
siguiente. Por eso el calendario se calcula sobre el instante objetivo y no
sobre el actual.

Se ejecuta asi:

    python -m src.features.build_features
"""

import sys

import numpy as np
import pandas as pd

from src import config
from src.logger import get_logger

log = get_logger(__name__)


class ErrorDeLeakage(Exception):
    """Se lanza cuando se pide una variable que mira hacia el futuro."""


def _validar_rezago(rezago, horizonte):
    """
    El guardian contra el leakage.

    Un rezago menor al horizonte usaria informacion que a la hora de predecir
    todavia no existe. Es el error mas facil de cometer en series de tiempo y
    el mas dificil de notar, porque el modelo da resultados excelentes.
    """
    if rezago < horizonte:
        raise ErrorDeLeakage(
            f"Se pidio un rezago de {rezago} h con un horizonte de {horizonte} h. "
            f"A la hora de predecir todavia no conocemos ese valor. "
            f"El rezago minimo permitido es {horizonte}."
        )


def _ciclico(valores, periodo):
    """
    Convierte algo que da vueltas (la hora, el dia) en dos numeros.

    Si metemos la hora como 0 a 23, el modelo cree que las 23h y las 0h estan
    lejisimos, cuando en realidad son consecutivas. Con seno y coseno el
    circulo queda cerrado.
    """
    angulo = 2 * np.pi * valores / periodo
    return np.sin(angulo), np.cos(angulo)


def construir_features(df, horizonte=None, con_objetivo=True):
    """
    Arma la tabla de variables.

    Parametros
    ----------
    df : DataFrame con las columnas de la capa processed y una columna
         'datetime'. Tiene que venir ordenado y con paso de una hora.
    horizonte : cuantas horas hacia adelante se pronostica. Por defecto sale
         de config.
    con_objetivo : si es True agrega la columna 'objetivo' con el valor real.
         La API la pone en False porque ahi todavia no existe la respuesta.

    Devuelve
    --------
    DataFrame con 'datetime', las variables y (si se pidio) 'objetivo'.
    """
    horizonte = horizonte or config.FORECAST_HORIZON
    t = config.TARGET

    d = df.copy()
    if "datetime" in d.columns:
        d = d.set_index("datetime")
    d = d.sort_index()

    # Trabajamos en logaritmo porque el benceno tiene una cola larga de picos.
    # El sesgo baja de 1.361 a -0.234. Al final se deshace con expm1.
    y = np.log1p(d[t])

    salida = pd.DataFrame(index=d.index)

    # --- Rezagos del benceno -------------------------------------------
    # y.shift(rezago - horizonte) es el valor de `rezago` horas antes del
    # momento objetivo. Con rezago = horizonte da shift(0), o sea el valor de
    # ahora, que es lo mas reciente que podemos usar.
    for rezago in config.LAGS_TARGET:
        _validar_rezago(rezago, horizonte)
        salida[f"benceno_lag{rezago}"] = y.shift(rezago - horizonte)

    # --- Medias moviles -------------------------------------------------
    # La ventana termina en la hora actual, asi que la mas reciente que puede
    # entrar es la de `horizonte` horas antes del objetivo.
    for ventana in config.VENTANAS_MOVILES:
        salida[f"benceno_media{ventana}h"] = y.rolling(ventana, min_periods=ventana).mean()

    # --- Tendencia ------------------------------------------------------
    # Cuanto subio o bajo entre ayer y anteayer a esta misma hora. Le dice al
    # modelo si la cosa viene en aumento.
    salida["benceno_tendencia"] = salida["benceno_lag24"] - salida["benceno_lag48"]

    # --- Sensores y ambientales, siempre rezagados ----------------------
    _validar_rezago(horizonte, horizonte)
    for columna in config.SENSORES_FEATURE:
        if columna in d.columns:
            salida[f"{columna}_lag{horizonte}"] = np.log1p(d[columna]).shift(0)

    for columna in config.AMBIENTALES_FEATURE:
        if columna in d.columns:
            salida[f"{columna}_lag{horizonte}"] = d[columna]

    # --- Calendario del momento objetivo --------------------------------
    # Esta es la unica parte que mira hacia adelante, y se puede: dentro de 24
    # horas sabemos perfectamente que hora y que dia va a ser.
    objetivo_en = d.index + pd.Timedelta(hours=horizonte)

    seno_hora, coseno_hora = _ciclico(objetivo_en.hour.to_numpy(), 24)
    salida["hora_seno"] = seno_hora
    salida["hora_coseno"] = coseno_hora

    seno_dia, coseno_dia = _ciclico(objetivo_en.dayofweek.to_numpy(), 7)
    salida["dia_seno"] = seno_dia
    salida["dia_coseno"] = coseno_dia

    # Va como decimal y no como entero a proposito: MLflow guarda el tipo de
    # cada columna y despues lo exige en la API. Un entero no admite nulos, asi
    # que si alguna vez llega un dato incompleto el servicio falla con un error
    # raro de esquema. Con decimal eso no pasa.
    salida["es_fin_de_semana"] = (objetivo_en.dayofweek >= 5).astype("float64")

    # --- El objetivo ----------------------------------------------------
    if con_objetivo:
        salida["objetivo"] = y.shift(-horizonte)

    salida = salida.reset_index()
    return salida


def columnas_de_entrada(tabla):
    """Los nombres de las variables, sin la fecha ni la respuesta."""
    return [c for c in tabla.columns if c not in ("datetime", "objetivo")]


def dividir_por_fecha(tabla):
    """
    Parte la tabla en los cinco tramos por fecha.

    Nunca al azar: es una serie de tiempo y mezclar seria entrenar con datos
    del futuro.
    """
    f = pd.to_datetime(tabla["datetime"])
    limites = [
        ("train", config.SPLIT_TRAIN_START, config.SPLIT_VALID_START),
        ("validation", config.SPLIT_VALID_START, config.SPLIT_BATCH1_START),
        ("batch1", config.SPLIT_BATCH1_START, config.SPLIT_BATCH2_START),
        ("batch2", config.SPLIT_BATCH2_START, config.SPLIT_BATCH3_START),
        ("batch3", config.SPLIT_BATCH3_START, None),
    ]
    tramos = {}
    for nombre, desde, hasta in limites:
        cond = f >= pd.Timestamp(desde)
        if hasta is not None:
            cond &= f < pd.Timestamp(hasta)
        tramos[nombre] = tabla.loc[cond].reset_index(drop=True)
    return tramos


def main():
    log.info("=" * 62)
    log.info("CONSTRUCCION DE VARIABLES")
    log.info("=" * 62)

    if not config.PROCESSED_FILE.exists():
        log.error("No existe %s. Corra primero la limpieza.", config.PROCESSED_FILE)
        return 1

    df = pd.read_parquet(config.PROCESSED_FILE)
    log.info("Entrada: %s filas", len(df))
    log.info("Horizonte de pronostico: %s horas", config.FORECAST_HORIZON)
    log.info("Rezagos del benceno: %s", config.LAGS_TARGET)

    tabla = construir_features(df)
    entradas = columnas_de_entrada(tabla)
    log.info("Variables construidas: %s", len(entradas))
    for c in entradas:
        log.info("   %s", c)

    # Las filas incompletas se botan: las primeras porque no hay historia
    # suficiente para el rezago de 168 horas, y las ultimas porque todavia no
    # se conoce la respuesta.
    antes = len(tabla)
    completas = tabla.dropna().reset_index(drop=True)
    log.info("Filas con todas las variables: %s de %s (se descartan %s)",
             len(completas), antes, antes - len(completas))

    tramos = dividir_por_fecha(completas)
    log.info("Reparto por tramo:")
    for nombre, parte in tramos.items():
        log.info("   %-11s %5d filas   %s a %s", nombre, len(parte),
                 parte["datetime"].min(), parte["datetime"].max())

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    completas.to_parquet(config.FEATURES_FILE, index=False)
    log.info("Guardado en %s (%s filas x %s columnas)",
             config.FEATURES_FILE, *completas.shape)

    log.info("Construccion de variables terminada sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())

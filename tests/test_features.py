"""
Pruebas de la construccion de variables.

La mas importante de todas es la del leakage. Un modelo con leakage da
resultados excelentes y esta mal, asi que no basta con mirarlo: hay que
probarlo automaticamente.

Se corren asi:

    pytest tests/ -v
"""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.features.build_features import (
    ErrorDeLeakage,
    _validar_rezago,
    columnas_de_entrada,
    construir_features,
    dividir_por_fecha,
)


@pytest.fixture
def datos():
    """
    Una serie horaria inventada, para no depender del archivo real.

    El ruido no es adorno: sin el, la serie seria un seno perfecto de 24 horas
    y el valor de ayer a esta hora seria identico al de hoy. Eso haria que la
    prueba de correlacion diera 1.0 sin que exista ningun leakage, y nos
    dejaria con una prueba que no sirve para nada.
    """
    fechas = pd.date_range("2004-03-10 18:00", periods=1000, freq="h")
    n = len(fechas)
    generador = np.random.default_rng(config.RANDOM_SEED)

    # Algo con forma de dia, para que los rezagos tengan sentido
    valores = (10
               + 5 * np.sin(2 * np.pi * np.arange(n) / 24)
               + np.linspace(0, 2, n)
               + generador.normal(0, 1.5, n))
    valores = np.clip(valores, 0.1, None)  # el benceno nunca es negativo

    return pd.DataFrame({
        "datetime": fechas,
        config.TARGET: valores,
        "PT08.S1(CO)": valores * 90,
        "PT08.S2(NMHC)": valores * 95,
        "PT08.S5(O3)": valores * 88,
        "T": 20 + 4 * np.sin(2 * np.pi * np.arange(n) / 24),
        "RH": 45 + 8 * np.cos(2 * np.pi * np.arange(n) / 24),
        "AH": np.full(n, 0.9),
    })


# --------------------------------------------------------------------------
# Leakage
# --------------------------------------------------------------------------

@pytest.mark.parametrize("rezago", [0, 1, 3, 12, 23])
def test_rechaza_rezagos_que_miran_al_futuro(rezago):
    """Cualquier rezago menor al horizonte tiene que ser rechazado."""
    with pytest.raises(ErrorDeLeakage):
        _validar_rezago(rezago, 24)


@pytest.mark.parametrize("rezago", [24, 25, 48, 168])
def test_acepta_rezagos_validos(rezago):
    _validar_rezago(rezago, 24)


def test_configuracion_no_tiene_rezagos_invalidos():
    """Los rezagos de config.py tienen que respetar la regla."""
    for rezago in config.LAGS_TARGET:
        assert rezago >= config.FORECAST_HORIZON, (
            f"El rezago {rezago} es menor al horizonte {config.FORECAST_HORIZON}"
        )


def test_alineacion_de_rezagos(datos):
    """
    Cada columna trae exactamente el valor de la hora que dice traer.

    Esta prueba es la que de verdad demuestra que no hay leakage: verifica
    contra la serie original, hora por hora.
    """
    H = config.FORECAST_HORIZON
    tabla = construir_features(datos, horizonte=H).set_index("datetime")
    original = np.log1p(datos.set_index("datetime")[config.TARGET])

    momento = tabla.index[500]

    esperado = {
        "objetivo": momento + pd.Timedelta(hours=H),
        "benceno_lag24": momento,
        "benceno_lag25": momento - pd.Timedelta(hours=1),
        "benceno_lag48": momento - pd.Timedelta(hours=24),
        "benceno_lag168": momento - pd.Timedelta(hours=144),
    }

    for columna, cuando in esperado.items():
        assert tabla.loc[momento, columna] == pytest.approx(original.loc[cuando]), (
            f"{columna} no trae el valor de {cuando}"
        )


def test_ninguna_variable_correlaciona_perfecto_con_el_objetivo(datos):
    """
    Si alguna variable correlaciona casi 1 con la respuesta, es que se colo el
    valor que queremos predecir.
    """
    tabla = construir_features(datos).dropna()
    for columna in columnas_de_entrada(tabla):
        r = abs(np.corrcoef(tabla[columna], tabla["objetivo"])[0, 1])
        assert r < 0.999, f"{columna} correlaciona {r:.4f} con el objetivo"


# --------------------------------------------------------------------------
# Esquema y formas
# --------------------------------------------------------------------------

def test_estan_todas_las_variables_esperadas(datos):
    tabla = construir_features(datos)
    entradas = columnas_de_entrada(tabla)

    for rezago in config.LAGS_TARGET:
        assert f"benceno_lag{rezago}" in entradas
    for ventana in config.VENTANAS_MOVILES:
        assert f"benceno_media{ventana}h" in entradas
    for calendario in ["hora_seno", "hora_coseno", "dia_seno", "dia_coseno",
                       "es_fin_de_semana"]:
        assert calendario in entradas


def test_sin_objetivo_para_la_api(datos):
    """La API no conoce la respuesta, asi que esa columna no debe aparecer."""
    tabla = construir_features(datos, con_objetivo=False)
    assert "objetivo" not in tabla.columns


def test_mismas_variables_con_y_sin_objetivo(datos):
    """
    El entrenamiento y la API tienen que ver exactamente las mismas variables,
    en el mismo orden. Si no, el modelo predice cualquier cosa en produccion.
    """
    con = columnas_de_entrada(construir_features(datos, con_objetivo=True))
    sin = columnas_de_entrada(construir_features(datos, con_objetivo=False))
    assert con == sin


def test_variables_ciclicas_en_rango(datos):
    tabla = construir_features(datos).dropna()
    for columna in ["hora_seno", "hora_coseno", "dia_seno", "dia_coseno"]:
        assert tabla[columna].between(-1, 1).all()
    assert tabla["es_fin_de_semana"].isin([0, 1]).all()


def test_sin_infinitos(datos):
    tabla = construir_features(datos).dropna()
    numericas = tabla.select_dtypes(include=[np.number])
    assert not np.isinf(numericas.to_numpy()).any()


# --------------------------------------------------------------------------
# Corte temporal
# --------------------------------------------------------------------------

def test_los_tramos_no_se_encabalgan(datos):
    """
    Ningun tramo puede compartir horas con otro, y tienen que ir en orden.
    Si se mezclaran, estariamos entrenando con datos del futuro.
    """
    tabla = construir_features(datos).dropna()
    tramos = dividir_por_fecha(tabla)

    orden = ["train", "validation", "batch1", "batch2", "batch3"]
    anterior = None
    for nombre in orden:
        parte = tramos[nombre]
        if parte.empty:
            continue
        if anterior is not None:
            assert parte["datetime"].min() > anterior, (
                f"El tramo {nombre} empieza antes de que termine el anterior"
            )
        anterior = parte["datetime"].max()


def test_la_suma_de_los_tramos_no_pierde_filas(datos):
    tabla = construir_features(datos).dropna()
    tramos = dividir_por_fecha(tabla)
    assert sum(len(p) for p in tramos.values()) == len(tabla)

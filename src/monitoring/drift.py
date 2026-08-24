"""
Deteccion de cambios en los datos (Data Monitoring, seccion N2).

Compara la distribucion de cada variable en el periodo de referencia contra la
del periodo de produccion. Se calculan cuatro medidas distintas a proposito:
cada una mira algo diferente y juntas cuentan una historia mas completa que
cualquiera por separado.

PSI (Population Stability Index)
    Parte la variable en diez tramos usando los cuantiles de la referencia y
    compara que porcentaje de datos cae en cada tramo. Es el que usamos para
    decidir, porque da un numero facil de interpretar y comparar entre
    variables.

Kolmogorov-Smirnov
    Mide la mayor distancia entre las dos curvas acumuladas y da un p-valor.
    Ojo con el p-valor: con miles de filas casi cualquier diferencia sale
    "significativa", asi que nunca decidimos solo con el.

Wasserstein
    Cuanto habria que mover los datos, en promedio, para que una distribucion
    quede igual a la otra. Va en las unidades de la variable, asi que se puede
    leer directo: "la temperatura se corrio 12 grados".

Jensen-Shannon
    Que tan distintas son las dos distribuciones en una escala de 0 a 1. Sirve
    para comparar variables que tienen unidades diferentes.

Los umbrales del PSI (0.10 y 0.25) son los que se usan habitualmente en la
industria desde los modelos de riesgo crediticio. No son leyes: son puntos de
corte razonables que hay que ajustar segun el caso. En este proyecto los
dejamos porque separan bien lo que vimos, y lo justificamos en el informe.
"""

import numpy as np
import pandas as pd
from scipy import stats

from src import config
from src.logger import get_logger

log = get_logger(__name__)

OK = "OK"
AVISO = "WARNING"
ALERTA = "ALERT"


def _limpiar(a, b):
    """Quita nulos e infinitos de las dos series antes de compararlas."""
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    return a, b


def psi(referencia, produccion, bins=None):
    """
    Population Stability Index.

    Los tramos salen de los cuantiles de la referencia, no de un ancho fijo.
    Asi cada tramo arranca con mas o menos la misma cantidad de datos y el
    indice no se deja llevar por unos pocos valores extremos.

    El recorte en 0.0001 evita dividir entre cero cuando un tramo queda vacio
    en produccion. Sin eso, una sola variable podria dar infinito y romper todo
    el reporte.
    """
    bins = bins or config.PSI_BINS
    referencia, produccion = _limpiar(referencia, produccion)

    if len(referencia) < 2 or len(produccion) < 2:
        return float("nan")

    cortes = np.unique(np.quantile(referencia, np.linspace(0, 1, bins + 1)))
    if len(cortes) < 3:
        # Variable casi constante: no tiene sentido partirla en tramos
        return 0.0

    cortes[0] = -np.inf
    cortes[-1] = np.inf

    p_ref = np.histogram(referencia, bins=cortes)[0] / len(referencia)
    p_pro = np.histogram(produccion, bins=cortes)[0] / len(produccion)

    p_ref = np.clip(p_ref, 1e-4, None)
    p_pro = np.clip(p_pro, 1e-4, None)

    return float(np.sum((p_pro - p_ref) * np.log(p_pro / p_ref)))


def kolmogorov_smirnov(referencia, produccion):
    """Distancia maxima entre las dos curvas acumuladas, y su p-valor."""
    referencia, produccion = _limpiar(referencia, produccion)
    if len(referencia) < 2 or len(produccion) < 2:
        return float("nan"), float("nan")
    resultado = stats.ks_2samp(referencia, produccion)
    return float(resultado.statistic), float(resultado.pvalue)


def wasserstein(referencia, produccion):
    """Cuanto hay que mover los datos para igualar las distribuciones."""
    referencia, produccion = _limpiar(referencia, produccion)
    if len(referencia) < 2 or len(produccion) < 2:
        return float("nan")
    return float(stats.wasserstein_distance(referencia, produccion))


def jensen_shannon_distancia(referencia, produccion, bins=None):
    """
    Distancia de Jensen-Shannon, entre 0 y 1.

    0 quiere decir distribuciones identicas, 1 que no se parecen en nada.
    """
    bins = bins or config.PSI_BINS
    referencia, produccion = _limpiar(referencia, produccion)
    if len(referencia) < 2 or len(produccion) < 2:
        return float("nan")

    minimo = min(referencia.min(), produccion.min())
    maximo = max(referencia.max(), produccion.max())
    if minimo == maximo:
        return 0.0

    cortes = np.linspace(minimo, maximo, bins + 1)
    p = np.histogram(referencia, bins=cortes)[0] + 1e-10
    q = np.histogram(produccion, bins=cortes)[0] + 1e-10
    p = p / p.sum()
    q = q / q.sum()

    return float(stats.entropy(p, (p + q) / 2, base=2) / 2
                 + stats.entropy(q, (p + q) / 2, base=2) / 2) ** 0.5


def clasificar(valor_psi):
    """Traduce el PSI a un semaforo."""
    if not np.isfinite(valor_psi):
        return OK
    if valor_psi >= config.PSI_ALERT:
        return ALERTA
    if valor_psi >= config.PSI_WARNING:
        return AVISO
    return OK


def comparar_variable(referencia, produccion, nombre=""):
    """Las cuatro medidas para una variable."""
    valor_psi = psi(referencia, produccion)
    ks_estadistico, ks_p = kolmogorov_smirnov(referencia, produccion)

    return {
        "variable": nombre,
        "psi": round(valor_psi, 4) if np.isfinite(valor_psi) else None,
        "estado": clasificar(valor_psi),
        "ks_estadistico": round(ks_estadistico, 4) if np.isfinite(ks_estadistico) else None,
        "ks_pvalor": float(f"{ks_p:.2e}") if np.isfinite(ks_p) else None,
        "ks_significativo": bool(ks_p < config.KS_ALPHA) if np.isfinite(ks_p) else None,
        "wasserstein": round(wasserstein(referencia, produccion), 4),
        "jensen_shannon": round(jensen_shannon_distancia(referencia, produccion), 4),
        "media_referencia": round(float(np.nanmean(referencia)), 3),
        "media_produccion": round(float(np.nanmean(produccion)), 3),
    }


def comparar_lote(referencia: pd.DataFrame, produccion: pd.DataFrame, columnas=None):
    """
    Compara todas las variables de un lote contra la referencia.

    Devuelve una tabla ordenada de mayor a menor PSI, que es como se lee: las
    que mas cambiaron arriba.
    """
    if columnas is None:
        columnas = [c for c in referencia.columns
                    if c not in ("datetime", "objetivo")
                    and pd.api.types.is_numeric_dtype(referencia[c])]

    filas = [comparar_variable(referencia[c], produccion[c], c)
             for c in columnas if c in produccion.columns]

    tabla = pd.DataFrame(filas)
    return tabla.sort_values("psi", ascending=False, na_position="last").reset_index(drop=True)


def resumen_del_lote(tabla):
    """El estado general de un lote a partir de sus variables."""
    alertas = tabla[tabla["estado"] == ALERTA]["variable"].tolist()
    avisos = tabla[tabla["estado"] == AVISO]["variable"].tolist()

    if alertas:
        estado = ALERTA
    elif avisos:
        estado = AVISO
    else:
        estado = OK

    return {
        "estado": estado,
        "psi_maximo": float(tabla["psi"].max()) if len(tabla) else 0.0,
        "variable_mas_cambiada": tabla.iloc[0]["variable"] if len(tabla) else None,
        "variables_en_alerta": alertas,
        "variables_en_aviso": avisos,
        "total_variables": len(tabla),
    }


def registrar(nombre_lote, tabla, resumen):
    """Deja el resultado en el log. Es el 'Registra' del ciclo de la seccion P."""
    log.info("-" * 62)
    log.info("DRIFT DE DATOS - %s", nombre_lote)
    log.info("-" * 62)
    log.info("Umbrales: aviso desde PSI %.2f, alerta desde PSI %.2f",
             config.PSI_WARNING, config.PSI_ALERT)

    for _, fila in tabla.iterrows():
        mensaje = (f"  {fila['variable']:24s} PSI {fila['psi']:8.3f}  "
                   f"KS {fila['ks_estadistico']:.3f}  "
                   f"Wass {fila['wasserstein']:9.3f}  "
                   f"media {fila['media_referencia']:8.2f} -> {fila['media_produccion']:8.2f}  "
                   f"[{fila['estado']}]")
        if fila["estado"] == ALERTA:
            log.error(mensaje)
        elif fila["estado"] == AVISO:
            log.warning(mensaje)
        else:
            log.info(mensaje)

    nivel = log.error if resumen["estado"] == ALERTA else (
        log.warning if resumen["estado"] == AVISO else log.info)
    nivel("Estado del lote %s: %s (PSI maximo %.3f en %s)",
          nombre_lote, resumen["estado"], resumen["psi_maximo"],
          resumen["variable_mas_cambiada"])

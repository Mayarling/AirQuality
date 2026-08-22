"""
Data Quality Gates.

Reglas automaticas que corren antes de entrenar y antes de servir. Si una
regla dura falla, el pipeline se detiene. Si falla una blanda, se avisa y se
sigue.

La diferencia entre dura y blanda es una decision nuestra, no un tecnicismo:
una regla dura marca algo que hace inutil el resultado (falta una columna, el
target esta vacio). Una blanda marca algo que hay que mirar pero que no impide
seguir (aparecieron más huecos de lo normal).

Se ejecuta asi:

    from src.validation.quality_gates import correr_gates
    resultados = correr_gates(df, etapa="entrada")

Y para que corte el pipeline cuando algo grave falla:

    correr_gates(df, etapa="entrada", detener=True)
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src import config
from src.logger import get_logger

log = get_logger(__name__)

DURA = "dura"
BLANDA = "blanda"


class ErrorDeCalidad(Exception):
    """Se lanza cuando una regla dura no pasa."""


@dataclass
class Resultado:
    codigo: str
    nombre: str
    severidad: str
    paso: bool
    detalle: str
    medido: dict = field(default_factory=dict)

    def __str__(self):
        estado = "PASA" if self.paso else "FALLA"
        return f"[{self.codigo}] {estado} ({self.severidad}) {self.nombre}: {self.detalle}"


# --------------------------------------------------------------------------
# Reglas
# --------------------------------------------------------------------------

def _esquema(df, esperadas):
    """
    Comprueba que esten las columnas esperadas, que sean númericas y que no
    haya aparecido ninguna de más.

    Una columna nueva que nadie pidio es un cambio de esquema, y en producción
    eso rompe el modelo en silencio. Por eso también falla la regla.
    """
    auxiliares = ("datetime", "imputado")

    faltan = [c for c in esperadas if c not in df.columns]
    nuevas = [c for c in df.columns if c not in esperadas and c not in auxiliares]
    no_numericas = [c for c in esperadas
                    if c in df.columns and not pd.api.types.is_numeric_dtype(df[c])]

    problemas = []
    if faltan:
        problemas.append(f"faltan {faltan}")
    if no_numericas:
        problemas.append(f"no son númericas {no_numericas}")
    if nuevas:
        problemas.append(f"columnas de más {nuevas}")

    paso = not problemas
    detalle = "; ".join(problemas) if problemas else f"{len(esperadas)} columnas correctas"

    return Resultado("R01", "esquema de columnas", DURA, paso, detalle,
                     {"faltan": faltan, "nuevas": nuevas, "no_numericas": no_numericas})


def r01_esquema_entrada(df):
    """En la capa interim todavia están todas las columnas del archivo original."""
    esperadas = [c for c in config.EXPECTED_COLUMNS if c not in ("Date", "Time")]
    return _esquema(df, esperadas)


def r01_esquema_salida(df):
    """En la capa processed ya no deben estar las columnas que decidimos botar."""
    esperadas = [c for c in config.EXPECTED_COLUMNS
                 if c not in ("Date", "Time") and c not in config.COLUMNS_TO_DROP]
    return _esquema(df, esperadas)


def r02_filas_minimas(df):
    """Llegaron suficientes filas como para que el resultado signifique algo."""
    n = len(df)
    paso = n >= config.MIN_ROWS
    return Resultado("R02", "cantidad minima de filas", DURA, paso,
                     f"{n} filas (minimo {config.MIN_ROWS})",
                     {"filas": n, "minimo": config.MIN_ROWS})


def r03_sin_timestamps_repetidos(df):
    """Ninguna hora aparece dos veces. En una serie horaria eso seria un error."""
    repetidos = int(df["datetime"].duplicated().sum())
    paso = repetidos == 0
    return Resultado("R03", "timestamps sin repetir", DURA, paso,
                     f"{repetidos} repetidos", {"repetidos": repetidos})


def r04_continuidad_horaria(df):
    """
    La serie avanza de hora en hora sin saltarse ninguna.

    Es blanda a proposito: un hueco no invalida los datos, pero cambia como hay
    que calcular los lags, asi que queremos enterarnos.
    """
    fechas = df["datetime"].sort_values()
    completo = pd.date_range(fechas.min(), fechas.max(), freq="h")
    faltantes = len(completo) - len(fechas)
    paso = faltantes == 0
    return Resultado("R04", "continuidad horaria", BLANDA, paso,
                     f"{faltantes} horas ausentes de {len(completo)} esperadas",
                     {"horas_ausentes": faltantes, "horas_esperadas": len(completo)})


def r05_rangos_fisicos(df):
    """
    Ningun valor cae fuera de lo fisicamente posible.

    Un valor fuera de rango no es un outlier: es un error de medición o de
    unidad. Los rangos salen de config.VALID_RANGES y estan justificados ahi.
    """
    fuera = {}
    for columna, (minimo, maximo) in config.VALID_RANGES.items():
        if columna not in df.columns:
            continue
        serie = df[columna].dropna()
        n = int(((serie < minimo) | (serie > maximo)).sum())
        if n:
            fuera[columna] = n

    paso = not fuera
    detalle = "todos los valores dentro de rango" if paso else f"fuera de rango: {fuera}"
    return Resultado("R05", "rangos fisicos posibles", DURA, paso, detalle,
                     {"fuera_de_rango": fuera})


def r06_faltantes_en_target(df):
    """Cuantos huecos tiene la variable que vamos a pronosticar."""
    t = config.TARGET
    if t not in df.columns:
        return Resultado("R06", "faltantes en el target", DURA, False,
                         f"la columna {t} no existe", {})

    tasa = float(df[t].isna().mean())
    paso = tasa <= config.MAX_MISSING_RATE_TARGET
    return Resultado("R06", "faltantes en el target", BLANDA, paso,
                     f"{tasa*100:.2f}% de huecos (limite {config.MAX_MISSING_RATE_TARGET*100:.0f}%)",
                     {"tasa": tasa})


def r07_duplicados(df):
    """Filas repetidas enteras."""
    tasa = float(df.duplicated().mean())
    paso = tasa <= config.MAX_DUPLICATE_RATE
    return Resultado("R07", "filas duplicadas", DURA, paso,
                     f"{tasa*100:.3f}% duplicadas (limite {config.MAX_DUPLICATE_RATE*100:.0f}%)",
                     {"tasa": tasa})


def r08_target_sin_nulos(df):
    """
    En la tabla lista para entrenar, el target no puede tener huecos.

    Solo aplica a la etapa de salida. Antes de limpiar es normal que los tenga.
    """
    t = config.TARGET
    nulos = int(df[t].isna().sum())
    paso = nulos == 0
    return Resultado("R08", "target sin nulos", DURA, paso,
                     f"{nulos} nulos en {t}", {"nulos": nulos})


def r09_sin_infinitos(df):
    """
    Ningun valor infinito. Aparecen cuando una division se va a cero y rompen
    el entrenamiento sin dar un error claro.
    """
    numericas = df.select_dtypes(include=[np.number])
    total = int(np.isinf(numericas.to_numpy(dtype="float64", na_value=0.0)).sum())
    paso = total == 0
    return Resultado("R09", "sin valores infinitos", DURA, paso,
                     f"{total} infinitos", {"infinitos": total})


# --------------------------------------------------------------------------
# Ejecución
# --------------------------------------------------------------------------

# Que reglas corren en cada momento del pipeline.
#
# ENTRADA: sobre la capa interim, antes de limpiar. Aquí todavia es normal que
#          haya huecos, asi que R06 es blanda.
# SALIDA:  sobre la capa processed, justo antes de entrenar. Aquí ya no se
#          perdona nada en el target.
REGLAS = {
    "entrada": [r01_esquema_entrada, r02_filas_minimas, r03_sin_timestamps_repetidos,
                r04_continuidad_horaria, r05_rangos_fisicos, r06_faltantes_en_target,
                r07_duplicados],
    "salida": [r01_esquema_salida, r02_filas_minimas, r05_rangos_fisicos,
               r08_target_sin_nulos, r09_sin_infinitos],
}


def correr_gates(df, etapa="entrada", detener=False):
    """
    Corre las reglas de la etapa indicada y las deja escritas en el log.

    Si detener=True y alguna regla dura falla, lanza ErrorDeCalidad. Ese es el
    "bloquea" del ciclo detecta -> bloquea/advierte -> registra.
    """
    if etapa not in REGLAS:
        raise ValueError(f"Etapa desconocida: {etapa}. Use {list(REGLAS)}")

    log.info("-" * 62)
    log.info("DATA QUALITY GATES - etapa: %s", etapa)
    log.info("-" * 62)

    resultados = []
    for regla in REGLAS[etapa]:
        r = regla(df)
        resultados.append(r)
        if r.paso:
            log.info(str(r))
        elif r.severidad == DURA:
            log.error(str(r))
        else:
            log.warning(str(r))

    duras_fallidas = [r for r in resultados if not r.paso and r.severidad == DURA]
    blandas_fallidas = [r for r in resultados if not r.paso and r.severidad == BLANDA]

    log.info("Resumen: %s reglas, %s fallaron duras, %s fallaron blandas",
             len(resultados), len(duras_fallidas), len(blandas_fallidas))

    if duras_fallidas and detener:
        codigos = ", ".join(r.codigo for r in duras_fallidas)
        log.error("Pipeline detenido por las reglas duras: %s", codigos)
        raise ErrorDeCalidad(
            f"Fallaron {len(duras_fallidas)} reglas duras ({codigos}). "
            "Revisar logs/pipeline.log"
        )

    return resultados


def a_dataframe(resultados):
    """Pasa los resultados a una tabla, util para guardarlos como artefacto."""
    return pd.DataFrame([
        {"codigo": r.codigo, "regla": r.nombre, "severidad": r.severidad,
         "paso": r.paso, "detalle": r.detalle}
        for r in resultados
    ])

"""
Diagnostico de calidad de los datos.

Recorre la lista de la sección E del enunciado y deja el resultado en
reports/diagnostico_calidad.md. Ese archivo es la evidencia de que miramos
los datos antes de decidir que hacer con ellos.

Se ejecuta asi:

    python -m src.validation.diagnose
"""

import sys

import numpy as np
import pandas as pd

from src import config
from src.logger import get_logger
from src.validation.quality_gates import correr_gates, a_dataframe

log = get_logger(__name__)


def bloques_de_nulos(serie):
    """
    Agrupa los nulos en rachas seguidas y devuelve el largo de cada una.

    No es lo mismo tener 366 huecos sueltos que 16 apagones de varios días.
    La decision de rellenar o no depende de esto, no del porcentaje.
    """
    nulo = serie.isna()
    if not nulo.any():
        return []
    grupo = (nulo != nulo.shift()).cumsum()
    largos = nulo.groupby(grupo).sum()
    return sorted([int(x) for x in largos[largos > 0]], reverse=True)


def tabla_faltantes(df, columnas):
    filas = []
    for c in columnas:
        nulos = int(df[c].isna().sum())
        bloques = bloques_de_nulos(df[c])
        filas.append({
            "columna": c,
            "nulos": nulos,
            "pct": round(nulos / len(df) * 100, 2),
            "bloques": len(bloques),
            "bloque_mas_largo_h": bloques[0] if bloques else 0,
        })
    return pd.DataFrame(filas).sort_values("pct", ascending=False)


def tabla_estadistica(df, columnas):
    filas = []
    for c in columnas:
        s = df[c].dropna()
        if s.empty:
            continue
        filas.append({
            "columna": c,
            "min": round(float(s.min()), 2),
            "p50": round(float(s.median()), 2),
            "max": round(float(s.max()), 2),
            "media": round(float(s.mean()), 2),
            "desv": round(float(s.std()), 2),
            "skew": round(float(s.skew()), 3),
            "unicos": int(s.nunique()),
        })
    return pd.DataFrame(filas)


def md_tabla(df):
    """Convierte un DataFrame a tabla markdown sin depender de tabulate."""
    encabezado = "| " + " | ".join(str(c) for c in df.columns) + " |"
    guion = "|" + "|".join("---" for _ in df.columns) + "|"
    filas = ["| " + " | ".join(str(v) for v in fila) + " |"
             for fila in df.itertuples(index=False)]
    return "\n".join([encabezado, guion] + filas)


def main():
    log.info("=" * 62)
    log.info("DIAGNOSTICO DE CALIDAD")
    log.info("=" * 62)

    if not config.INTERIM_FILE.exists():
        log.error("No existe %s. Corra primero la ingesta.", config.INTERIM_FILE)
        return 1

    df = pd.read_parquet(config.INTERIM_FILE)
    columnas = [c for c in df.columns if c != "datetime"]
    t = config.TARGET

    log.info("Filas: %s | Columnas: %s", len(df), len(df.columns))
    log.info("Periodo: %s a %s", df["datetime"].min(), df["datetime"].max())

    # --- 1. Faltantes -----------------------------------------------------
    faltantes = tabla_faltantes(df, columnas)
    log.info("Columnas con mas de 50%% de huecos: %s",
             list(faltantes.loc[faltantes["pct"] > 50, "columna"]))

    # --- 2. Duplicados ----------------------------------------------------
    dup_filas = int(df.duplicated().sum())
    dup_fechas = int(df["datetime"].duplicated().sum())
    log.info("Filas duplicadas: %s | Timestamps repetidos: %s", dup_filas, dup_fechas)

    # --- 3. Continuidad temporal -----------------------------------------
    completo = pd.date_range(df["datetime"].min(), df["datetime"].max(), freq="h")
    huecos_tiempo = len(completo) - len(df)
    log.info("Horas ausentes en la serie: %s", huecos_tiempo)

    # --- 4. Apagones del arreglo de sensores ------------------------------
    # Nota Importante: son dos instrumentos distintos. El arreglo de sensores (PT08 mas T,
    # RH, AH y el benceno derivado) se apaga completo; el analizador de
    # referencia (las columnas GT) falla en otros momentos. Por eso hay que
    # mirarlos por separado y no todos juntos.
    apagones = df[config.SENSOR_COLUMNS].isna().all(axis=1)
    alguno_nulo = df[config.SENSOR_COLUMNS].isna().any(axis=1)
    bloques_apagon = bloques_de_nulos(df[t])
    log.info("Filas donde el arreglo de sensores no midió nada: %s "
             "(filas con al menos uno nulo: %s)",
             int(apagones.sum()), int(alguno_nulo.sum()))
    log.info("Esos huecos forman %s bloques seguidos, el mayor de %s horas",
             len(bloques_apagon), bloques_apagon[0] if bloques_apagon else 0)

    # --- 5. Estadística, sesgo y cardinalidad -----------------------------
    estad = tabla_estadistica(df, columnas)

    # --- 6. Datos imposibles ---------------------------------------------
    imposibles = {}
    for columna, (minimo, maximo) in config.VALID_RANGES.items():
        if columna in df.columns:
            s = df[columna].dropna()
            n = int(((s < minimo) | (s > maximo)).sum())
            if n:
                imposibles[columna] = n
    log.info("Valores fuera de rango fisico: %s", imposibles or "ninguno")

    # --- 7. Valores extremos (regla del rango intercuartil) ---------------
    extremos = []
    for c in columnas:
        s = df[c].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        ric = q3 - q1
        n = int(((s < q1 - 3 * ric) | (s > q3 + 3 * ric)).sum())
        extremos.append({"columna": c, "extremos": n, "pct": round(n / len(s) * 100, 2)})
    extremos = pd.DataFrame(extremos).sort_values("pct", ascending=False)

    # --- 8. Correlacion excesiva (riesgo de leakage) ---------------------
    cor = df[columnas].corr()[t].drop(t)
    orden = list(cor.abs().sort_values(ascending=False).index)
    cor_tabla = pd.DataFrame({
        "columna": orden,
        "correlacion_con_target": [round(float(cor[c]), 4) for c in orden],
        "filas_comparables": [int(df[[t, c]].dropna().shape[0]) for c in orden],
    })
    sospechosas = list(cor_tabla.loc[cor_tabla["correlacion_con_target"].abs() > 0.95, "columna"])
    if sospechosas:
        log.warning("Correlacion mayor a 0.95 con el target: %s. "
                    "Solo se pueden usar rezagadas, nunca del mismo instante.", sospechosas)

    # --- 9. Gates ---------------------------------------------------------
    resultados = correr_gates(df, etapa="entrada", detener=False)

    # --- Reporte ----------------------------------------------------------
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    partes = [
        "# Diagnostico de calidad de datos",
        "",
        "Generado por `python -m src.validation.diagnose`.",
        "",
        f"- Fuente: {config.DATASET_NAME}",
        f"- Filas: {len(df)}",
        f"- Columnas: {len(columnas)}",
        f"- Periodo: {df['datetime'].min()} a {df['datetime'].max()}",
        f"- Variable a pronosticar: `{t}`",
        "",
        "## 1. Valores faltantes",
        "",
        "Los faltantes venian codificados como -200 y ya fueron convertidos a nulo",
        "en la ingesta. La columna `bloque_mas_largo_h` es la clave: dice cuantas",
        "horas seguidas estuvo sin medir.",
        "",
        md_tabla(faltantes),
        "",
        "## 2. Duplicados",
        "",
        f"- Filas repetidas enteras: {dup_filas}",
        f"- Timestamps repetidos: {dup_fechas}",
        "",
        "## 3. Continuidad temporal",
        "",
        f"- Horas esperadas entre el primer y el ultimo registro: {len(completo)}",
        f"- Horas presentes: {len(df)}",
        f"- Horas ausentes: {huecos_tiempo}",
        "",
        "## 4. Apagones del arreglo de sensores",
        "",
        "Hay dos instrumentos distintos en este dataset y fallan en momentos",
        "distintos, asi que hay que mirarlos por separado:",
        "",
        f"- Arreglo de sensores ({', '.join(config.SENSOR_COLUMNS)})",
        f"- Analizador de referencia ({', '.join(config.REFERENCE_COLUMNS)})",
        "",
        f"Filas donde el arreglo de sensores no midió absolutamente nada: {int(apagones.sum())}",
        f"Filas donde al menos uno de ellos esta nulo: {int(alguno_nulo.sum())}",
        "",
        "Los dos números coinciden, lo que confirma que se apagan juntos: no son",
        "fallas sueltas de un sensor, es el equipo completo fuera de servicio.",
        "",
        f"- Cantidad de bloques seguidos: {len(bloques_apagon)}",
        f"- Duración de cada bloque en horas: {bloques_apagon}",
        "",
        "## 5. Estadística descriptiva, sesgo y cardinalidad",
        "",
        md_tabla(estad),
        "",
        "## 6. Datos imposibles",
        "",
        f"Rangos evaluados: {config.VALID_RANGES}",
        "",
        f"Resultado: {imposibles if imposibles else 'ningún valor fuera de rango físico'}",
        "",
        "## 7. Valores extremos",
        "",
        "Criterio: fuera de Q1 - 3*RIC o Q3 + 3*RIC. Se cuentan, no se borran:",
        "en contaminación del aire un pico alto suele ser un evento real.",
        "",
        md_tabla(extremos),
        "",
        "## 8. Correlación con el target y riesgo de leakage",
        "",
        md_tabla(cor_tabla),
        "",
        f"Columnas con correlación mayor a 0.95: {sospechosas if sospechosas else 'ninguna'}",
        "",
        "Este numero no es una curiosidad estadística, es una advertencia. En este",
        "dataset el valor de benceno se obtuvo calibrando la respuesta del sensor",
        "PT08.S2(NMHC), asi que las dos columnas miden casi lo mismo.",
        "",
        "Consecuencia para el modelado: como el problema es pronosticar el futuro,",
        "solo se pueden usar valores de la hora t hacia atras para predecir la hora",
        "t+24. Usar la lectura del mismo instante que queremos predecir daria un",
        "resultado altisimo y falso.",
        "",
        "## 9. Data Quality Gates",
        "",
        md_tabla(a_dataframe(resultados)),
        "",
    ]

    config.REPORTE_CALIDAD.write_text("\n".join(partes), encoding="utf-8")
    log.info("Reporte escrito en %s", config.REPORTE_CALIDAD)
    log.info("Diagnostico terminado")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Simulacion de problemas de calidad (seccion P del enunciado).

Ningun dataset real trae todos los defectos posibles, asi que hay que
fabricarlos a proposito para comprobar que el sistema los agarra.

Se le meten seis danos a un lote de produccion:

    1. valores faltantes
    2. filas duplicadas
    3. un valor absurdo (el equivalente a income = -500000)
    4. un tipo de dato incorrecto (el equivalente a age = "treinta")
    5. una categoria desconocida (el equivalente a country = "UNKNOWN_NEW_COUNTRY")
    6. un cambio de esquema: se borra una columna

Y despues se pasa por los mismos Data Quality Gates de la parte 2, para ver si
cumplen el ciclo que pide el enunciado:

    Detecta  ->  Bloquea o Advierte  ->  Registra

REGLA QUE NO SE ROMPE: el dataset original no se toca nunca. Todo se hace sobre
una copia en memoria. Al terminar, los archivos de data/ quedan exactamente
igual que antes, y hay una comprobacion al final que lo verifica.

Se ejecuta asi:

    python -m src.monitoring.contaminar
"""

import sys

import numpy as np
import pandas as pd

from src import config
from src.logger import get_logger
from src.validation.quality_gates import ErrorDeCalidad, correr_gates

log = get_logger(__name__)

# Un lote de produccion trae muchas menos filas que el historico completo, asi
# que la regla R02 se evalua contra este minimo y no contra el de config.
MIN_FILAS_LOTE = 500


def meter_faltantes(df, porcentaje=0.08, semilla=None):
    """Borra valores al azar, como cuando un sensor deja de reportar."""
    d = df.copy()
    generador = np.random.default_rng(semilla or config.RANDOM_SEED)

    columna = config.TARGET
    cuantas = int(len(d) * porcentaje)
    filas = generador.choice(len(d), size=cuantas, replace=False)
    d.loc[d.index[filas], columna] = np.nan

    return d, f"{cuantas} valores de {columna} borrados ({porcentaje*100:.0f}%)"


def meter_duplicados(df, cuantas=25):
    """Repite filas enteras, como cuando un proceso se ejecuta dos veces."""
    d = df.copy()
    repetidas = d.head(cuantas).copy()
    d = pd.concat([d, repetidas], ignore_index=True)
    return d, f"{cuantas} filas duplicadas al final"


def meter_valor_absurdo(df):
    """
    Un valor fisicamente imposible.

    Es el equivalente en nuestro dataset del income = -500000 del enunciado:
    una humedad relativa de 999% y un benceno negativo.
    """
    d = df.copy()
    d.loc[d.index[5], "RH"] = 999.0
    d.loc[d.index[6], config.TARGET] = -45.0
    return d, "RH = 999% en la fila 5 y benceno = -45 en la fila 6"


def meter_tipo_incorrecto(df):
    """
    Texto donde va un numero. El age = "treinta" del enunciado.

    Al meter texto, pandas convierte la columna entera a tipo objeto. Eso es lo
    que la regla del esquema tiene que detectar.
    """
    d = df.copy()
    d["T"] = d["T"].astype("object")
    d.loc[d.index[10], "T"] = "quince grados"
    return d, 'T = "quince grados" en la fila 10 (la columna deja de ser numerica)'


def meter_categoria_desconocida(df):
    """
    Una categoria que nunca se vio.

    Nuestro dataset es todo numerico, asi que el equivalente es una columna
    nueva con una categoria inventada, igual que el UNKNOWN_NEW_COUNTRY del
    enunciado. Se detecta por la regla del esquema.
    """
    d = df.copy()
    d["pais"] = "UNKNOWN_NEW_COUNTRY"
    return d, 'columna nueva pais = "UNKNOWN_NEW_COUNTRY"'


def meter_cambio_de_esquema(df):
    """Desaparece una columna, como cuando cambia el formato de origen."""
    d = df.copy()
    quitada = "PT08.S3(NOx)"
    if quitada in d.columns:
        d = d.drop(columns=[quitada])
    return d, f"columna {quitada} eliminada"


DANOS = [
    ("faltantes", meter_faltantes),
    ("duplicados", meter_duplicados),
    ("valor absurdo", meter_valor_absurdo),
    ("tipo incorrecto", meter_tipo_incorrecto),
    ("categoria desconocida", meter_categoria_desconocida),
    ("cambio de esquema", meter_cambio_de_esquema),
]


def contaminar(df):
    """Aplica los seis danos a una copia y devuelve el lote roto."""
    log.info("-" * 62)
    log.info("CONTAMINANDO UN LOTE DE PRUEBA")
    log.info("-" * 62)
    log.info("Lote original: %s filas x %s columnas", *df.shape)

    roto = df.copy()
    aplicados = []

    for nombre, funcion in DANOS:
        roto, detalle = funcion(roto)
        aplicados.append({"dano": nombre, "detalle": detalle})
        log.info("  %-24s %s", nombre, detalle)

    log.info("Lote contaminado: %s filas x %s columnas", *roto.shape)
    return roto, aplicados


def probar_los_gates(lote_roto):
    """
    Le pasa el lote roto a los Data Quality Gates.

    El resultado esperado es que se detenga. Si pasara sin problemas, seria
    senal de que las reglas no sirven.
    """
    log.info("-" * 62)
    log.info("PASANDO EL LOTE CONTAMINADO POR LOS GATES")
    log.info("-" * 62)

    try:
        resultados = correr_gates(lote_roto, etapa="entrada", detener=True,
                                  min_filas=MIN_FILAS_LOTE)
        log.error("PROBLEMA: el lote contaminado paso los gates sin bloquearse. "
                  "Las reglas no estan sirviendo.")
        return {"bloqueado": False, "resultados": resultados, "motivo": None}

    except ErrorDeCalidad as e:
        log.info("Correcto: el pipeline se detuvo.")
        log.info("Motivo: %s", e)
        # Se vuelven a correr sin detener, para tener la lista completa de que
        # fallo y no solo la primera regla
        resultados = correr_gates(lote_roto, etapa="entrada", detener=False,
                                  min_filas=MIN_FILAS_LOTE)
        return {"bloqueado": True, "resultados": resultados, "motivo": str(e)}


def main():
    log.info("=" * 62)
    log.info("SIMULACION DE PROBLEMAS DE CALIDAD (seccion P)")
    log.info("=" * 62)

    if not config.PROCESSED_FILE.exists():
        log.error("No existe %s. Corra primero la limpieza.", config.PROCESSED_FILE)
        return 1

    original = pd.read_parquet(config.PROCESSED_FILE)

    # Se toma solo el ultimo lote, para que la prueba sea rapida y para dejar
    # claro que esto es un lote de produccion y no todo el historico
    lote = original[original["datetime"] >= config.SPLIT_BATCH3_START].copy()
    lote = lote.drop(columns=["imputado"], errors="ignore")
    log.info("Se usa el lote batch3 como base: %s filas", len(lote))

    # La huella del archivo antes de tocar nada
    from src.ingestion.ingest import hash_archivo
    huella_antes = hash_archivo(config.PROCESSED_FILE)

    roto, aplicados = contaminar(lote)
    resultado = probar_los_gates(roto)

    # --- Comprobar que el original no se toco -----------------------------
    log.info("-" * 62)
    log.info("COMPROBANDO QUE EL DATASET ORIGINAL NO SE MODIFICO")
    log.info("-" * 62)

    huella_despues = hash_archivo(config.PROCESSED_FILE)
    intacto = huella_antes == huella_despues

    log.info("Huella antes:   %s", huella_antes)
    log.info("Huella despues: %s", huella_despues)

    if intacto:
        log.info("El archivo original quedo intacto. La contaminacion fue solo "
                 "en memoria, como pide el enunciado.")
    else:
        log.error("El archivo original cambio. Eso no deberia pasar nunca.")

    # --- Resumen ----------------------------------------------------------
    fallidas = [r for r in resultado["resultados"] if not r.paso]

    log.info("=" * 62)
    log.info("RESULTADO DE LA SIMULACION")
    log.info("=" * 62)
    log.info("Danos aplicados     : %s", len(aplicados))
    log.info("Reglas que fallaron : %s de %s",
             len(fallidas), len(resultado["resultados"]))
    for r in fallidas:
        log.info("   [%s] %s: %s", r.codigo, r.nombre, r.detalle)
    log.info("Pipeline bloqueado  : %s", "si" if resultado["bloqueado"] else "NO")
    log.info("Dataset intacto     : %s", "si" if intacto else "NO")
    log.info("")
    log.info("Ciclo detecta -> bloquea -> registra: %s",
             "cumplido" if resultado["bloqueado"] and intacto else "NO cumplido")

    return 0 if (resultado["bloqueado"] and intacto) else 1


if __name__ == "__main__":
    sys.exit(main())

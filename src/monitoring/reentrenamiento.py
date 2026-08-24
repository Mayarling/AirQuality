"""
Cuando reentrenar el modelo (seccion Q del enunciado).

La regla es que hacen falta LAS DOS COSAS a la vez:

    SI  hay drift en los datos  Y  el modelo se degrado
    ENTONCES  reentrenar

No una sola. Y esa es justamente la pregunta que el enunciado pide justificar:
por que Data Drift no es lo mismo que Model Degradation.

La respuesta la tenemos medida con nuestros propios datos:

    lote      PSI maximo    degradacion del MAE
    batch1        1.671            +87.7%
    batch2        6.175            +51.4%
    batch3        3.265             -2.5%

El lote 3 tiene el segundo drift mas grande de los tres y sin embargo el modelo
anda MEJOR que en validacion. Si el disparador mirara solo el PSI, habriamos
reentrenado un modelo que estaba funcionando bien, gastando tiempo y arriesgando
empeorarlo.

Por que puede pasar eso:

  - El modelo aprendio la relacion entre las variables, no sus valores. Si
    aprendio que con temperatura baja hay menos benceno, un invierno frio entra
    dentro de lo que ya sabe aunque la distribucion de temperatura se haya
    movido muchisimo.
  - El drift puede estar en variables que al modelo casi no le importan.
  - Y al reves tambien pasa: el modelo se puede degradar sin drift ninguno, si
    cambia la relacion entre las variables y lo que queremos predecir. Eso se
    llama concept drift y el PSI no lo ve.

Por eso el monitoreo de datos y el de modelo son los dos necesarios y ninguno
reemplaza al otro. El de datos avisa temprano, incluso antes de saber si el
pronostico fue bueno; el de modelo confirma si de verdad hubo daño, pero solo se
puede medir cuando ya pasaron las 24 horas y se sabe que ocurrio.
"""

import numpy as np

from src import config
from src.logger import get_logger

log = get_logger(__name__)

REENTRENAR = "REENTRENAR"
VIGILAR = "VIGILAR"
REVISAR_DATOS = "REVISAR_DATOS"
TODO_BIEN = "TODO_BIEN"


def decidir(psi_maximo, degradacion, filas):
    """
    Decide que hacer con un lote.

    Parametros
    ----------
    psi_maximo  : el PSI mas alto entre todas las variables del lote
    degradacion : cuanto empeoro el MAE respecto de validacion (0.30 = 30% peor)
    filas       : cuantas filas trae el lote

    Devuelve un diccionario con la decision y el motivo escrito.
    """
    if filas < config.MIN_FILAS_PARA_DECIDIR:
        return {
            "decision": VIGILAR,
            "motivo": (f"solo {filas} filas, muy pocas para decidir "
                       f"(minimo {config.MIN_FILAS_PARA_DECIDIR})"),
            "hay_drift": None,
            "hay_degradacion": None,
        }

    hay_drift = bool(np.isfinite(psi_maximo) and psi_maximo >= config.PSI_ALERT)
    hay_degradacion = bool(np.isfinite(degradacion)
                           and degradacion > config.DEGRADACION_MAXIMA)

    if hay_drift and hay_degradacion:
        decision = REENTRENAR
        motivo = (f"los datos cambiaron (PSI {psi_maximo:.3f} por encima de "
                  f"{config.PSI_ALERT}) Y el modelo se degrado "
                  f"({degradacion*100:+.1f}%, limite {config.DEGRADACION_MAXIMA*100:.0f}%)")

    elif hay_drift and not hay_degradacion:
        decision = VIGILAR
        motivo = (f"los datos cambiaron (PSI {psi_maximo:.3f}) pero el modelo "
                  f"sigue respondiendo bien ({degradacion*100:+.1f}%). "
                  f"Reentrenar aqui seria botar un modelo que funciona")

    elif not hay_drift and hay_degradacion:
        decision = REVISAR_DATOS
        motivo = (f"el modelo se degrado ({degradacion*100:+.1f}%) sin que las "
                  f"distribuciones cambien (PSI {psi_maximo:.3f}). Puede ser "
                  f"concept drift, un problema de calidad o un periodo raro. "
                  f"Hay que mirarlo antes de reentrenar")

    else:
        decision = TODO_BIEN
        motivo = (f"sin cambios importantes (PSI {psi_maximo:.3f}, "
                  f"desempeño {degradacion*100:+.1f}%)")

    return {
        "decision": decision,
        "motivo": motivo,
        "hay_drift": hay_drift,
        "hay_degradacion": hay_degradacion,
        "psi_maximo": round(float(psi_maximo), 4) if np.isfinite(psi_maximo) else None,
        "degradacion": round(float(degradacion), 4) if np.isfinite(degradacion) else None,
    }


def evaluar_lotes(resumenes_drift, tabla_desempeno):
    """
    Aplica la decision a cada lote de produccion.

    resumenes_drift : diccionario {nombre_lote: resumen de drift.resumen_del_lote}
    tabla_desempeno : la tabla de model_metrics.desempeno_por_lote
    """
    decisiones = []

    for _, fila in tabla_desempeno.iterrows():
        lote = fila["tramo"]
        if lote not in resumenes_drift:
            continue

        resultado = decidir(
            psi_maximo=resumenes_drift[lote]["psi_maximo"],
            degradacion=fila.get("degradacion", np.nan),
            filas=fila["filas"],
        )
        resultado["lote"] = lote
        resultado["mae"] = fila["mae"]
        decisiones.append(resultado)

    return decisiones


def registrar(decisiones):
    """Deja las decisiones en el log."""
    log.info("-" * 62)
    log.info("DECISION DE REENTRENAMIENTO")
    log.info("-" * 62)
    log.info("Regla: se reentrena solo si hay drift Y degradacion a la vez")
    log.info("  drift       : PSI maximo >= %.2f", config.PSI_ALERT)
    log.info("  degradacion : MAE mas de %.0f%% peor que en validacion",
             config.DEGRADACION_MAXIMA * 100)
    log.info("")

    for d in decisiones:
        mensaje = f"  {d['lote']:10s} {d['decision']:14s} {d['motivo']}"
        if d["decision"] == REENTRENAR:
            log.error(mensaje)
        elif d["decision"] in (VIGILAR, REVISAR_DATOS):
            log.warning(mensaje)
        else:
            log.info(mensaje)

    hay_que_reentrenar = [d["lote"] for d in decisiones
                          if d["decision"] == REENTRENAR]
    if hay_que_reentrenar:
        log.error("Se dispara el reentrenamiento por: %s",
                  ", ".join(hay_que_reentrenar))
    else:
        log.info("No hace falta reentrenar con estos lotes")

    return hay_que_reentrenar

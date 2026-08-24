"""
Seguimiento del desempeño del modelo (Model Monitoring, seccion N3).

Para un problema de pronostico las metricas que corresponden son MAE y RMSE
medidas a lo largo del tiempo, no una sola vez. Un modelo puede tener buen
promedio general y estar fallando feo desde hace dos semanas.

Aqui se calcula el desempeño por lote y tambien por ventanas de tiempo, para
poder ver si el error viene subiendo o si fue un mal dia suelto.

Una aclaracion importante para el informe: esto solo se puede hacer cuando ya
se conoce lo que de verdad paso. Con un horizonte de 24 horas, el error de un
pronostico recien se puede medir un dia despues. Mientras tanto el unico
monitoreo posible es el de datos, y por eso los dos son necesarios.
"""

import numpy as np
import pandas as pd

from src import config
from src.logger import get_logger
from src.training.evaluate import calcular_metricas

log = get_logger(__name__)


def desempeno_por_lote(modelo, tramos, columnas, referencia="validation"):
    """
    Metricas del modelo en cada tramo, comparadas contra el tramo de referencia.

    La columna 'degradacion' es la que importa: cuanto peor esta el modelo
    ahora respecto de cuando lo aprobamos.
    """
    filas = []
    mae_referencia = None

    for nombre, parte in tramos.items():
        if nombre == "train" or len(parte) == 0:
            continue

        predicho = modelo.predict(parte[columnas])
        metricas = calcular_metricas(parte["objetivo"], predicho)

        if nombre == referencia:
            mae_referencia = metricas["mae"]

        filas.append({
            "tramo": nombre,
            "filas": len(parte),
            "desde": parte["datetime"].min(),
            "hasta": parte["datetime"].max(),
            "mae": round(metricas["mae"], 3),
            "rmse": round(metricas["rmse"], 3),
            "mape": round(metricas["mape"], 1),
            "r2": round(metricas["r2"], 3),
            "sesgo": round(metricas["sesgo"], 3),
        })

    tabla = pd.DataFrame(filas)
    if mae_referencia:
        tabla["degradacion"] = (tabla["mae"] / mae_referencia - 1).round(4)
    return tabla


def desempeno_por_ventana(modelo, datos, columnas, dias=7):
    """
    Error del modelo agrupado por ventanas de varios dias.

    Sirve para ver la tendencia. Si el MAE sube ventana tras ventana, el modelo
    se esta degradando de verdad; si sube y baja, es ruido.
    """
    if len(datos) == 0:
        return pd.DataFrame()

    d = datos.copy()
    d["prediccion"] = modelo.predict(d[columnas])
    d["ventana"] = pd.to_datetime(d["datetime"]).dt.to_period(f"{dias}D").dt.start_time

    filas = []
    for ventana, grupo in d.groupby("ventana"):
        if len(grupo) < 24:  # menos de un dia no dice nada
            continue
        metricas = calcular_metricas(grupo["objetivo"], grupo["prediccion"])
        filas.append({
            "ventana": ventana,
            "horas": len(grupo),
            "mae": round(metricas["mae"], 3),
            "rmse": round(metricas["rmse"], 3),
            "r2": round(metricas["r2"], 3),
        })

    return pd.DataFrame(filas)


def registrar(tabla):
    """Deja el desempeño en el log."""
    log.info("-" * 62)
    log.info("DESEMPENO DEL MODELO POR TRAMO")
    log.info("-" * 62)
    log.info("%-12s %6s %8s %8s %8s %8s %12s",
             "tramo", "filas", "MAE", "RMSE", "MAPE", "R2", "degradacion")

    for _, f in tabla.iterrows():
        degradacion = f.get("degradacion")
        texto = f"{degradacion*100:+.1f}%" if pd.notna(degradacion) else "-"

        mensaje = (f"{f['tramo']:<12} {f['filas']:6d} {f['mae']:8.3f} "
                   f"{f['rmse']:8.3f} {f['mape']:7.1f}% {f['r2']:8.3f} {texto:>12}")

        if pd.notna(degradacion) and degradacion > config.DEGRADACION_MAXIMA:
            log.warning(mensaje + "  <- por encima del limite")
        else:
            log.info(mensaje)

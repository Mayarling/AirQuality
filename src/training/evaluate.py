"""
Metricas y graficos de evaluacion.

Todo lo que mide un modelo esta aqui, para que el entrenamiento, el monitoreo y
el informe usen exactamente el mismo calculo. Si el MAE se calculara distinto
en dos lados, las comparaciones no significarian nada.

Las metricas se devuelven en ug/m3, no en logaritmo. El modelo entrena sobre el
logaritmo porque le va mejor, pero un error de "0.31 en escala log" no le dice
nada a nadie. Con expm1 se deshace la transformacion y queda "3.05 ug/m3".
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from src import config
from src.eda.plots import AZUL, NARANJA, GRIS, TINTA, TINTA_SUAVE, estilo


def a_escala_original(valores_log):
    """Deshace el logaritmo. Es lo contrario de np.log1p."""
    return np.expm1(valores_log)


def calcular_metricas(real_log, predicho_log, prefijo=""):
    """
    Metricas de un pronostico.

    Se calculan en las dos escalas: las de ug/m3 son las que se reportan y se
    entienden, las de log son las que el modelo optimiza.
    """
    real = a_escala_original(np.asarray(real_log, dtype="float64"))
    pred = a_escala_original(np.asarray(predicho_log, dtype="float64"))

    error = real - pred
    error_log = np.asarray(real_log) - np.asarray(predicho_log)

    # MAPE: se deja fuera lo que este por debajo de 0.5 ug/m3, porque dividir
    # entre casi cero infla el porcentaje y deja de significar algo.
    medibles = real >= 0.5
    if medibles.sum() > 0:
        mape = float(np.mean(np.abs(error[medibles] / real[medibles])) * 100)
    else:
        mape = float("nan")

    varianza = np.var(real)
    r2 = float(1 - np.mean(error ** 2) / varianza) if varianza > 0 else float("nan")

    metricas = {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error ** 2))),
        "mape": mape,
        "r2": r2,
        "mae_log": float(np.mean(np.abs(error_log))),
        "rmse_log": float(np.sqrt(np.mean(error_log ** 2))),
        "sesgo": float(np.mean(error)),  # positivo = el modelo se queda corto
        "n": int(len(real)),
    }

    if prefijo:
        metricas = {f"{prefijo}_{k}": v for k, v in metricas.items()}
    return metricas


def formatear(metricas):
    """Una linea legible para el log."""
    def buscar(nombre):
        for k, v in metricas.items():
            if k.endswith(nombre):
                return v
        return float("nan")

    return (f"MAE {buscar('mae'):5.2f}  RMSE {buscar('rmse'):5.2f}  "
            f"MAPE {buscar('mape'):5.1f}%  R2 {buscar('r2'):6.3f}")


# --------------------------------------------------------------------------
# Graficos que se guardan como artefactos en MLflow
# --------------------------------------------------------------------------

def grafico_residuos(real_log, predicho_log, nombre_modelo, ruta):
    """
    El residual plot que pide la seccion I.

    Dos paneles: los errores contra lo predicho, y como se reparten. Si los
    puntos formaran un embudo o una curva, seria senal de que al modelo le
    falta estructura.
    """
    estilo()
    real = a_escala_original(real_log)
    pred = a_escala_original(predicho_log)
    residuo = real - pred

    fig, ejes = plt.subplots(1, 2, figsize=(11, 3.8))

    ejes[0].scatter(pred, residuo, s=6, alpha=0.28, color=AZUL, edgecolors="none")
    ejes[0].axhline(0, color=NARANJA, linewidth=1.6)
    ejes[0].set_xlabel("valor pronosticado (ug/m3)")
    ejes[0].set_ylabel("error (real - pronosticado)")
    ejes[0].set_title("Errores contra lo pronosticado")
    ejes[0].grid(axis="y")

    ejes[1].hist(residuo, bins=60, color=AZUL, edgecolor="white", linewidth=0.4)
    ejes[1].axvline(0, color=NARANJA, linewidth=1.6)
    ejes[1].set_xlabel("error (ug/m3)")
    ejes[1].set_ylabel("horas")
    ejes[1].set_title(f"Reparto de los errores   (media {residuo.mean():+.2f})")
    ejes[1].grid(axis="y")

    fig.suptitle(f"Residuos - {nombre_modelo}", fontsize=12, color=TINTA)
    fig.tight_layout()
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return ruta


def grafico_real_vs_predicho(real_log, predicho_log, nombre_modelo, ruta):
    """Cada hora como un punto. La diagonal es el acierto perfecto."""
    estilo()
    real = a_escala_original(real_log)
    pred = a_escala_original(predicho_log)

    fig, ax = plt.subplots(figsize=(5.2, 5))
    ax.scatter(real, pred, s=7, alpha=0.3, color=AZUL, edgecolors="none")

    tope = max(real.max(), pred.max()) * 1.03
    ax.plot([0, tope], [0, tope], color=NARANJA, linewidth=1.6)
    ax.text(tope * 0.97, tope * 0.9, "acierto\nperfecto", fontsize=9,
            color=NARANJA, ha="right", va="top")

    ax.set_xlim(0, tope)
    ax.set_ylim(0, tope)
    ax.set_xlabel("benceno real (ug/m3)")
    ax.set_ylabel("benceno pronosticado (ug/m3)")
    ax.set_title(f"Real contra pronosticado - {nombre_modelo}")
    ax.grid()

    fig.tight_layout()
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return ruta


def grafico_serie(fechas, real_log, predicho_log, nombre_modelo, ruta, dias=21):
    """
    Un pedazo de la serie con las dos curvas encima.

    Es el grafico que mas dice en la defensa: se ve de una si el modelo sigue
    la forma del dia o si solo predice el promedio.
    """
    estilo()
    horas = dias * 24
    f = fechas[-horas:]
    real = a_escala_original(real_log[-horas:])
    pred = a_escala_original(predicho_log[-horas:])

    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.plot(f, real, color=AZUL, linewidth=1.7, label="real")
    ax.plot(f, pred, color=NARANJA, linewidth=1.7, label="pronosticado")
    ax.set_ylabel("benceno (ug/m3)")
    ax.set_title(f"Ultimos {dias} dias - {nombre_modelo}")
    ax.grid(axis="y")
    ax.legend(frameon=False, fontsize=9)

    fig.tight_layout()
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return ruta


def grafico_importancias(nombres, valores, nombre_modelo, ruta):
    """Que variables usa mas el modelo."""
    estilo()
    orden = np.argsort(valores)
    nombres = [nombres[i] for i in orden]
    valores = np.asarray(valores)[orden]

    fig, ax = plt.subplots(figsize=(8, 0.34 * len(nombres) + 1.2))
    ax.barh(nombres, valores, color=AZUL, height=0.66)
    ax.set_xlabel("importancia")
    ax.set_title(f"Peso de cada variable - {nombre_modelo}")
    ax.grid(axis="x")

    for y, v in enumerate(valores):
        ax.text(v + valores.max() * 0.012, y, f"{v:.3f}",
                va="center", fontsize=8, color=TINTA)

    ax.set_xlim(0, valores.max() * 1.18)
    fig.tight_layout()
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return ruta


def grafico_comparacion_modelos(resumen, ruta):
    """
    El MAE de cada modelo en validacion, con el baseline marcado.

    Una sola serie, ordenada de mejor a peor. El baseline va en gris para que
    se vea de un golpe cuales le ganan.
    """
    estilo()
    orden = sorted(resumen, key=lambda r: r["mae_validation"])
    nombres = [r["modelo"] for r in orden]
    valores = [r["mae_validation"] for r in orden]
    colores = [GRIS if "baseline" in n else AZUL for n in nombres]

    fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(nombres) + 1.6))
    barras = ax.barh(nombres[::-1], valores[::-1], color=colores[::-1], height=0.6)
    ax.set_xlabel("MAE en validacion (ug/m3) - menos es mejor")
    ax.set_title("Comparacion de modelos")
    ax.grid(axis="x")

    for barra, valor in zip(barras, valores[::-1]):
        ax.text(valor + max(valores) * 0.012,
                barra.get_y() + barra.get_height() / 2,
                f"{valor:.2f}", va="center", fontsize=9, color=TINTA)

    ax.set_xlim(0, max(valores) * 1.16)
    fig.tight_layout()
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return ruta

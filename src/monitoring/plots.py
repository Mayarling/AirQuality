"""
Graficos del monitoreo.

Mismos colores y mismo estilo que los del analisis exploratorio, para que el
informe se vea como un solo trabajo y no como pedazos pegados.
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.eda.plots import (AQUA, AZUL, GRIS, NARANJA, TINTA, TINTA_SUAVE,
                           FIGURAS_DIR, estilo)


def _guardar(fig, nombre):
    FIGURAS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURAS_DIR / f"{nombre}.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def psi_por_lote(tablas, nombre="08_psi_por_lote"):
    """
    El PSI de cada variable en los tres lotes.

    Tres series, una por lote, en el orden fijo de la paleta. Las lineas de los
    umbrales van punteadas y con su etiqueta, para que se lea sin leyenda
    adicional.
    """
    estilo()
    if not tablas:
        return

    lotes = list(tablas)
    colores = [AZUL, NARANJA, AQUA]

    # Se ordenan las variables por el PSI mas alto que alcanzan en cualquier lote
    variables = tablas[lotes[0]]["variable"].tolist()
    maximos = {v: max(float(t.loc[t["variable"] == v, "psi"].iloc[0] or 0)
                      for t in tablas.values()) for v in variables}
    variables = sorted(variables, key=lambda v: maximos[v])

    y = np.arange(len(variables))
    alto = 0.8 / len(lotes)

    fig, ax = plt.subplots(figsize=(9.5, 0.42 * len(variables) + 1.8))

    for i, (lote, color) in enumerate(zip(lotes, colores)):
        t = tablas[lote].set_index("variable")
        valores = [float(t.loc[v, "psi"] or 0) for v in variables]
        ax.barh(y + i * alto - 0.4 + alto / 2, valores, height=alto * 0.9,
                color=color, label=lote)

    ax.set_yticks(y)
    ax.set_yticklabels(variables, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("PSI (escala logaritmica)")
    ax.set_title("Cuanto cambio cada variable respecto de la referencia")
    ax.grid(axis="x")

    for umbral, texto, color in [(config.PSI_WARNING, "aviso", TINTA_SUAVE),
                                 (config.PSI_ALERT, "alerta", NARANJA)]:
        ax.axvline(umbral, color=color, linewidth=1.2, linestyle=(0, (4, 3)))
        ax.text(umbral, len(variables) - 0.3, f" {texto} {umbral}", fontsize=8,
                color=color, va="top")

    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _guardar(fig, nombre)


def drift_contra_desempeno(resumenes, desempeno, nombre="09_drift_vs_desempeno"):
    """
    El grafico que demuestra que drift y degradacion son cosas distintas.

    Dos paneles en vez de dos ejes en el mismo grafico: las dos medidas tienen
    escalas que no se pueden comparar, y ponerlas juntas daria una impresion
    falsa de que una sigue a la otra.
    """
    estilo()

    lotes = [l for l in ["batch1", "batch2", "batch3"] if l in resumenes]
    if not lotes:
        return

    psis = [resumenes[l]["psi_maximo"] for l in lotes]
    d = desempeno.set_index("tramo")
    degradaciones = [float(d.loc[l, "degradacion"]) * 100 if l in d.index else 0
                     for l in lotes]

    fig, ejes = plt.subplots(1, 2, figsize=(10, 3.8))

    barras = ejes[0].bar(lotes, psis, color=AZUL, width=0.55)
    ejes[0].axhline(config.PSI_ALERT, color=NARANJA, linewidth=1.2,
                    linestyle=(0, (4, 3)))
    ejes[0].text(len(lotes) - 0.5, config.PSI_ALERT, f" alerta {config.PSI_ALERT}",
                 fontsize=8, color=NARANJA, va="bottom", ha="right")
    ejes[0].set_ylabel("PSI mas alto del lote")
    ejes[0].set_title("Cuanto cambiaron los datos")
    ejes[0].grid(axis="y")
    for b, v in zip(barras, psis):
        ejes[0].text(b.get_x() + b.get_width() / 2, v + max(psis) * 0.02,
                     f"{v:.2f}", ha="center", fontsize=9, color=TINTA)

    colores = [NARANJA if v > config.DEGRADACION_MAXIMA * 100 else AZUL
               for v in degradaciones]
    barras = ejes[1].bar(lotes, degradaciones, color=colores, width=0.55)
    ejes[1].axhline(0, color=TINTA_SUAVE, linewidth=0.9)
    ejes[1].axhline(config.DEGRADACION_MAXIMA * 100, color=NARANJA,
                    linewidth=1.2, linestyle=(0, (4, 3)))
    ejes[1].set_ylabel("cambio del MAE contra validacion (%)")
    ejes[1].set_title("Cuanto empeoro el modelo")
    ejes[1].grid(axis="y")
    for b, v in zip(barras, degradaciones):
        ejes[1].text(b.get_x() + b.get_width() / 2,
                     v + (3 if v >= 0 else -8),
                     f"{v:+.1f}%", ha="center", fontsize=9, color=TINTA)

    ejes[1].margins(y=0.22)
    fig.suptitle("Que los datos cambien no significa que el modelo se dañe",
                 fontsize=12, color=TINTA)
    fig.tight_layout()
    _guardar(fig, nombre)


def error_en_el_tiempo(ventanas, nombre="10_error_en_el_tiempo"):
    """El MAE por ventanas de una semana."""
    estilo()
    if ventanas is None or len(ventanas) == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.plot(ventanas["ventana"], ventanas["mae"], color=AZUL, linewidth=2,
            marker="o", markersize=5, markeredgecolor="white")
    ax.set_ylabel("MAE (ug/m3)")
    ax.set_title("Error del modelo por semana")
    ax.grid(axis="y")
    ax.tick_params(axis="x", rotation=30, labelsize=8)

    primera = ventanas["mae"].iloc[0]
    ax.axhline(primera, color=TINTA_SUAVE, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(ventanas["ventana"].iloc[0], primera, " primera semana",
            fontsize=8, color=TINTA_SUAVE, va="bottom")

    _guardar(fig, nombre)


def distribucion_referencia_vs_lotes(referencia, tramos, lotes, variable,
                                     nombre="11_distribucion_por_lote"):
    """
    Como se corre la distribucion de una variable de un periodo a otro.

    Es el grafico que hace visible lo que el PSI resume en un numero.
    """
    estilo()
    if variable not in referencia.columns:
        return

    fig, ax = plt.subplots(figsize=(9.5, 3.6))

    ax.hist(referencia[variable].dropna(), bins=40, density=True, color=GRIS,
            alpha=0.85, label="referencia")

    for lote, color in zip(lotes, [AZUL, NARANJA, AQUA]):
        parte = tramos.get(lote)
        if parte is None or len(parte) == 0:
            continue
        ax.hist(parte[variable].dropna(), bins=40, density=True, histtype="step",
                linewidth=2, color=color, label=lote)

    ax.set_xlabel(variable)
    ax.set_ylabel("densidad")
    ax.set_title(f"La distribucion de {variable} se corre de un periodo a otro")
    ax.grid(axis="y")
    ax.legend(frameon=False, fontsize=9)

    _guardar(fig, nombre)

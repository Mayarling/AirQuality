"""
Dibuja el diagrama de arquitectura del proyecto.

El README lleva el mismo diagrama escrito en Mermaid, que GitHub dibuja solo.
Este script existe para tener una imagen suelta que se pueda meter en la
presentacion, porque en PowerPoint no se puede pegar Mermaid.

Los dos diagramas tienen que decir lo mismo. Si se cambia uno, hay que cambiar
el otro.

Regla que nos pusimos: cada caja lleva escrito debajo el archivo del repositorio
que la implementa. Si una caja no tiene archivo, no va en el diagrama.

Se ejecuta asi:

    python scripts/diagrama.py

Deja la imagen en reports/figuras/12_arquitectura.png
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.eda.plots import AQUA, AZUL, GRIS, NARANJA, TINTA, TINTA_SUAVE

SALIDA = config.REPORTS_DIR / "figuras" / "12_arquitectura.png"

# Ancho y alto de una caja, en las unidades del lienzo (0 a 100)
ANCHO = 21.0
ALTO = 10.0

# Colores segun el papel de cada caja
RELLENOS = {
    "datos": ("#e8f1fb", AZUL),      # archivos que se guardan en disco
    "codigo": ("#ffffff", TINTA_SUAVE),  # modulos que hacen el trabajo
    "modelo": ("#e6f6f0", AQUA),     # todo lo que tiene que ver con el modelo
    "aviso": ("#fdeee7", NARANJA),   # cortes y alertas
    "externo": ("#f2f1ee", GRIS),    # lo que no es nuestro
}


def caja(ax, x, y, titulo, archivo, papel="codigo"):
    """Dibuja una caja centrada en (x, y) y devuelve su posicion."""
    relleno, borde = RELLENOS[papel]

    ax.add_patch(FancyBboxPatch(
        (x - ANCHO / 2, y - ALTO / 2), ANCHO, ALTO,
        boxstyle="round,pad=0.35,rounding_size=1.2",
        linewidth=1.4, edgecolor=borde, facecolor=relleno, zorder=2,
    ))

    ax.text(x, y + 2.4, titulo, ha="center", va="center", fontsize=9.5,
            fontweight="medium", color=TINTA, zorder=3)
    ax.text(x, y - 2.1, archivo, ha="center", va="center", fontsize=6.8,
            color=TINTA_SUAVE, family="monospace", linespacing=1.45, zorder=3)

    return (x, y)


def flecha(ax, desde, hasta, texto=None, punteada=False, curva=0.0):
    """
    Une dos cajas. La flecha arranca y termina en el borde, no en el centro.

    La etiqueta no va encima de la flecha sino por fuera de la fila: entre dos
    cajas de la misma fila queda muy poco espacio y el texto terminaba pisando
    el titulo de la caja de al lado.
    """
    x1, y1 = desde
    x2, y2 = hasta

    horizontal = abs(x2 - x1) > abs(y2 - y1)

    if horizontal:
        borde = ANCHO / 2 + 0.6
        p1 = (x1 + borde * (1 if x2 > x1 else -1), y1)
        p2 = (x2 - borde * (1 if x2 > x1 else -1), y2)
    else:
        borde = ALTO / 2 + 0.6
        p1 = (x1, y1 + borde * (1 if y2 > y1 else -1))
        p2 = (x2, y2 - borde * (1 if y2 > y1 else -1))

    color = NARANJA if punteada else TINTA_SUAVE

    ax.add_patch(FancyArrowPatch(
        p1, p2,
        arrowstyle="-|>", mutation_scale=13,
        linewidth=1.2, color=color,
        linestyle=(0, (4, 3)) if punteada else "solid",
        connectionstyle=f"arc3,rad={curva}", zorder=1,
        shrinkA=0, shrinkB=0,
    ))

    if texto:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        if horizontal:
            ax.text(mx, my + ALTO / 2 + 1.4, texto, ha="center", va="bottom",
                    fontsize=7, color=color, zorder=3)
        else:
            ax.text(mx + 1.6, my, texto, ha="left", va="center",
                    fontsize=7, color=color, zorder=3)


def banda(ax, y, titulo):
    """El rotulo de la etapa, a la izquierda del lienzo."""
    ax.text(-3.5, y, titulo, ha="right", va="center", fontsize=8.5,
            fontweight="medium", color=AZUL)


def main():
    fig, ax = plt.subplots(figsize=(17.5, 11.5))
    ax.set_xlim(-20, 140)
    ax.set_ylim(-14, 100)
    ax.axis("off")

    fig.patch.set_facecolor("white")

    # Cuatro columnas y cuatro filas. El recorrido va en zigzag: la fila 1 de
    # izquierda a derecha, la 2 de derecha a izquierda, y asi. De esa forma el
    # paso de una fila a la siguiente es una flecha corta hacia abajo y no una
    # diagonal que cruza el dibujo entero.
    cx = [12, 39, 66, 93]
    fy = [88, 66, 44, 22]
    lado = 122          # columna suelta de la derecha
    abajo = 1           # fila suelta de abajo

    # --- Fila 1: de la fuente a las reglas de calidad ---------------------
    banda(ax, fy[0], "1 · Ingesta\ny calidad")

    n_fuente = caja(ax, cx[0], fy[0], "Fuente externa",
                    "archive.ics.uci.edu", "externo")
    n_ingesta = caja(ax, cx[1], fy[0], "Ingesta",
                     "src/ingestion/\ningest.py")
    n_raw = caja(ax, cx[2], fy[0], "Datos crudos",
                 "data/raw/\nAirQualityUCI.csv", "datos")
    n_gates = caja(ax, cx[3], fy[0], "Data Quality Gates",
                   "src/validation/\nquality_gates.py")

    flecha(ax, n_fuente, n_ingesta)
    flecha(ax, n_ingesta, n_raw)
    flecha(ax, n_raw, n_gates)

    # La simulacion de danos y el corte del pipeline, a la derecha
    n_sim = caja(ax, lado, fy[0], "Simulacion de danos",
                 "src/monitoring/\ncontaminar.py", "aviso")
    n_stop = caja(ax, lado, fy[1], "Pipeline detenido",
                  "ErrorDeCalidad", "aviso")

    flecha(ax, n_sim, n_gates, "las mismas reglas", punteada=True)
    flecha(ax, n_gates, n_stop, punteada=True)
    ax.text(lado - ANCHO / 2 - 2, fy[1] + 3, "si falla\nuna regla dura",
            ha="right", va="center", fontsize=7, color=NARANJA)
    ax.text(lado, fy[0] - ALTO / 2 - 2.2,
            "toma un lote de data/processed\ny lo rompe solo en memoria",
            ha="center", va="top", fontsize=6.6, color=TINTA_SUAVE)

    # --- Fila 2: limpieza, analisis y variables (de derecha a izquierda) --
    banda(ax, fy[1], "2 · Limpieza\ny variables")

    n_clean = caja(ax, cx[3], fy[1], "Limpieza",
                   "src/cleaning/\nclean.py")
    n_proc = caja(ax, cx[2], fy[1], "Datos limpios",
                  "data/processed/\nair_quality_limpio.parquet", "datos")
    n_eda = caja(ax, cx[1], fy[1], "Analisis exploratorio",
                 "notebooks/\n01_eda.ipynb")
    n_feat = caja(ax, cx[0], fy[1], "Variables sin leakage",
                  "src/features/\nbuild_features.py")

    flecha(ax, n_gates, n_clean, "pasa")
    flecha(ax, n_clean, n_proc)
    flecha(ax, n_proc, n_eda)
    flecha(ax, n_eda, n_feat)

    # --- Fila 3: entrenamiento, MLflow y modelo ---------------------------
    banda(ax, fy[2], "3 · Modelo\ny registro")

    n_fe = caja(ax, cx[0], fy[2], "Variables",
                "data/processed/\nfeatures.parquet", "datos")
    n_train = caja(ax, cx[1], fy[2], "Entrenamiento",
                   "src/training/\ntrain.py", "modelo")
    n_mlflow = caja(ax, cx[2], fy[2], "MLflow",
                    "Experiment\n+ Model Registry", "modelo")
    n_export = caja(ax, cx[3], fy[2], "Modelo en produccion",
                    "models/\nproduccion/", "modelo")

    flecha(ax, n_feat, n_fe)
    flecha(ax, n_fe, n_train)
    flecha(ax, n_train, n_mlflow)
    flecha(ax, n_mlflow, n_export, "alias produccion")

    # --- Fila 4: servicio y monitoreo (de derecha a izquierda) ------------
    banda(ax, fy[3], "4 · Servicio\ny monitoreo")

    n_docker = caja(ax, cx[3], fy[3], "Contenedor",
                    "Dockerfile", "externo")
    n_api = caja(ax, cx[2], fy[3], "API",
                 "src/api/\nmain.py")
    n_mon = caja(ax, cx[1], fy[3], "Monitoreo de datos\ny de modelo",
                 "src/monitoring/\nrun_monitoring.py", "modelo")
    n_dec = caja(ax, cx[0], fy[3], "Decision",
                 "src/monitoring/\nreentrenamiento.py", "aviso")

    flecha(ax, n_export, n_docker)
    flecha(ax, n_docker, n_api)
    flecha(ax, n_api, n_mon, "System: GET /metrics")
    flecha(ax, n_mon, n_dec)

    # Los lotes de produccion salen del mismo archivo de variables. Esta flecha
    # va con coordenadas puestas a mano porque no une dos cajas alineadas.
    ax.add_patch(FancyArrowPatch(
        (cx[0] + 5, fy[2] - ALTO / 2 - 0.6),
        (cx[1] - 4, fy[3] + ALTO / 2 + 0.6),
        arrowstyle="-|>", mutation_scale=13, linewidth=1.2, color=TINTA_SUAVE,
        connectionstyle="arc3,rad=-0.22", zorder=1, shrinkA=0, shrinkB=0,
    ))
    ax.text(cx[1] - 6, fy[3] + ALTO / 2 + 4, "los lotes de produccion",
            ha="right", va="bottom", fontsize=7, color=TINTA_SUAVE)

    # --- El reporte y el ciclo de reentrenamiento -------------------------
    n_rep = caja(ax, cx[0], abajo, "Reporte",
                 "reports/\nmonitoreo.md", "datos")
    flecha(ax, n_dec, n_rep)

    # Si la decision dice REENTRENAR, se vuelve al entrenamiento
    ax.add_patch(FancyArrowPatch(
        (cx[0] + ANCHO / 2 + 0.6, fy[3] + 2.5),
        (cx[1] - ANCHO / 2 - 0.6, fy[2] - 2.5),
        arrowstyle="-|>", mutation_scale=13, linewidth=1.4, color=NARANJA,
        linestyle=(0, (4, 3)),
        connectionstyle="arc3,rad=0.3", zorder=1, shrinkA=0, shrinkB=0,
    ))
    ax.text(cx[0] + ANCHO / 2 + 1, fy[3] + 15.5, "si dice REENTRENAR",
            ha="left", va="center", fontsize=7, color=NARANJA)

    # --- Titulo y leyenda -------------------------------------------------
    ax.text(-20, 98, "Arquitectura del proyecto",
            ha="left", va="center", fontsize=16, color=TINTA)
    ax.text(-20, 94.2,
            "Grupo 8  ·  pronostico de benceno a 24 horas  ·  "
            "cada caja lleva debajo el archivo del repositorio que la implementa",
            ha="left", va="center", fontsize=8.5, color=TINTA_SUAVE)

    etiquetas = [("archivos en disco", "datos"), ("codigo", "codigo"),
                 ("modelo", "modelo"), ("cortes y alertas", "aviso"),
                 ("fuera del repositorio", "externo")]
    for i, (texto, papel) in enumerate(etiquetas):
        relleno, borde = RELLENOS[papel]
        x = -20 + i * 30
        ax.add_patch(FancyBboxPatch(
            (x, -12.0), 3.2, 2.2,
            boxstyle="round,pad=0.15,rounding_size=0.5",
            linewidth=1.2, edgecolor=borde, facecolor=relleno))
        ax.text(x + 4.6, -10.9, texto, ha="left", va="center", fontsize=8,
                color=TINTA_SUAVE)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Diagrama guardado en {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

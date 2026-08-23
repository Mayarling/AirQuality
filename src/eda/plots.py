"""
Graficos del analisis exploratorio.

Estan aqui y no sueltos en el notebook por dos razones: para que el notebook
quede corto y se lea como un informe, y para poder volver a generar las mismas
figuras despues y guardarlas como artefactos en MLflow.

Cada funcion devuelve la figura y ademas la guarda en reports/figuras/.
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

from src import config

FIGURAS_DIR = config.REPORTS_DIR / "figuras"

# Tres colores, en este orden y siempre el mismo. No se rota ni se agregan mas:
# si hiciera falta una cuarta serie, se separa en varios graficos.
AZUL = "#2a78d6"
NARANJA = "#eb6834"
AQUA = "#1baf7a"

TINTA = "#0b0b0b"
TINTA_SUAVE = "#52514e"
GRIS = "#c9c8c3"


def estilo():
    """Ajustes comunes: rejilla tenue, sin marcos, tipografia discreta."""
    matplotlib.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": GRIS,
        "axes.labelcolor": TINTA_SUAVE,
        "axes.titlesize": 12,
        "axes.titleweight": "medium",
        "axes.titlecolor": TINTA,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": TINTA_SUAVE,
        "ytick.color": TINTA_SUAVE,
        "grid.color": GRIS,
        "grid.linewidth": 0.6,
        "grid.alpha": 0.5,
        "font.size": 10,
        "figure.dpi": 110,
        "savefig.bbox": "tight",
    })


def _guardar(fig, nombre):
    FIGURAS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURAS_DIR / f"{nombre}.png", dpi=140)
    return fig


def _cortes():
    """Las fechas de corte, como objetos de fecha."""
    return {
        "VALIDATION": pd.Timestamp(config.SPLIT_VALID_START),
        "BATCH 1": pd.Timestamp(config.SPLIT_BATCH1_START),
        "BATCH 2": pd.Timestamp(config.SPLIT_BATCH2_START),
        "BATCH 3": pd.Timestamp(config.SPLIT_BATCH3_START),
    }


# --------------------------------------------------------------------------

def serie_completa(df, nombre="01_serie_completa"):
    """La serie entera con las lineas de corte marcadas."""
    estilo()
    s = df.set_index("datetime")[config.TARGET]
    diario = s.resample("D").mean()

    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.plot(diario.index, diario.values, color=AZUL, linewidth=1.4)
    ax.set_ylabel("benceno (ug/m3)")
    ax.set_title("Promedio diario de benceno, marzo 2004 a abril 2005")
    ax.grid(axis="y")

    tope = ax.get_ylim()[1]
    for etiqueta, fecha in _cortes().items():
        ax.axvline(fecha, color=TINTA_SUAVE, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(fecha, tope * 0.97, " " + etiqueta, fontsize=8,
                color=TINTA_SUAVE, va="top", ha="left")

    return _guardar(fig, nombre)


def distribucion_target(df, nombre="02_distribucion_target"):
    """El target en su escala original y en logaritmo, uno al lado del otro."""
    estilo()
    s = df[config.TARGET].dropna()
    log_s = np.log1p(s)

    fig, ejes = plt.subplots(1, 2, figsize=(10, 3.4))

    ejes[0].hist(s, bins=60, color=AZUL, edgecolor="white", linewidth=0.4)
    ejes[0].set_title(f"Escala original   (sesgo {s.skew():.2f})")
    ejes[0].set_xlabel("benceno (ug/m3)")

    ejes[1].hist(log_s, bins=60, color=NARANJA, edgecolor="white", linewidth=0.4)
    ejes[1].set_title(f"Con logaritmo   (sesgo {log_s.skew():.2f})")
    ejes[1].set_xlabel("log(1 + benceno)")

    for e in ejes:
        e.set_ylabel("horas")
        e.grid(axis="y")

    fig.tight_layout()
    return _guardar(fig, nombre)


def perfil_horario(df, nombre="03_perfil_horario"):
    """Promedio por hora del dia."""
    estilo()
    s = df.set_index("datetime")[config.TARGET]
    h = s.groupby(s.index.hour).mean()

    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.plot(h.index, h.values, color=AZUL, linewidth=2,
            marker="o", markersize=5, markerfacecolor=AZUL, markeredgecolor="white")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("hora del dia")
    ax.set_ylabel("benceno promedio (ug/m3)")
    ax.set_title("Doble pico diario: entrada y salida del trabajo")
    ax.grid(axis="y")

    # Un poco de aire arriba para que la etiqueta del pico no toque el titulo
    ax.set_ylim(h.min() - 1.8, h.max() * 1.16)

    # (hora, desplazamiento, alineacion) para que ninguna etiqueta toque la linea
    etiquetas = [
        (int(h.idxmax()), (12, 12), "left"),
        (int(h.idxmin()), (0, 13), "center"),
        (8, (-14, 10), "right"),
    ]
    for hora, desfase, alineacion in etiquetas:
        ax.annotate(f"{hora}h: {h[hora]:.1f}", (hora, h[hora]),
                    textcoords="offset points", xytext=desfase,
                    ha=alineacion, fontsize=9, color=TINTA)

    return _guardar(fig, nombre)


def perfil_semanal(df, nombre="04_perfil_semanal"):
    """Promedio por dia de la semana."""
    estilo()
    s = df.set_index("datetime")[config.TARGET]
    d = s.groupby(s.index.dayofweek).mean()
    nombres = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

    colores = [AZUL] * 5 + [NARANJA] * 2

    fig, ax = plt.subplots(figsize=(9, 3.4))
    barras = ax.bar(nombres, d.values, color=colores, width=0.68)
    ax.set_ylabel("benceno promedio (ug/m3)")
    ax.set_title("Entre semana contra fin de semana")
    ax.grid(axis="y")

    for barra, valor in zip(barras, d.values):
        ax.text(barra.get_x() + barra.get_width() / 2, valor + 0.25,
                f"{valor:.1f}", ha="center", fontsize=9, color=TINTA)

    ax.set_ylim(0, max(d.values) * 1.16)
    return _guardar(fig, nombre)


def autocorrelacion(df, max_lag=180, horizonte=None, nombre="05_autocorrelacion"):
    """
    Autocorrelacion del target, separando los rezagos que si podemos usar de
    los que no.

    Con un horizonte de 24 horas, a la hora t no conocemos nada entre t+1 y
    t+23. Por eso todos los rezagos menores al horizonte quedan fuera, por muy
    altos que se vean.
    """
    from statsmodels.tsa.stattools import acf

    estilo()
    horizonte = horizonte or config.FORECAST_HORIZON

    s = np.log1p(df.set_index("datetime")[config.TARGET])
    s = s.interpolate(limit_area="inside").dropna()
    valores = acf(s, nlags=max_lag, fft=True)

    lags = np.arange(len(valores))
    usable = lags >= horizonte

    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.bar(lags[~usable], valores[~usable], color=GRIS, width=0.9,
           label=f"no disponible (menos de {horizonte} h)")
    ax.bar(lags[usable], valores[usable], color=AZUL, width=0.9,
           label=f"utilizable (desde {horizonte} h)")

    ax.axhline(0, color=TINTA_SUAVE, linewidth=0.8)
    ax.set_xlabel("rezago en horas")
    ax.set_ylabel("autocorrelacion")
    ax.set_title("Que tanto se parece la serie a si misma horas atras")
    ax.grid(axis="y")
    ax.legend(frameon=False, fontsize=9, loc="upper right")

    for lag in [horizonte, 48, 168]:
        if lag < len(valores):
            ax.annotate(f"{lag}h: {valores[lag]:.2f}", (lag, valores[lag]),
                        textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=9, color=TINTA)

    return _guardar(fig, nombre)


def ranking_predictores(ranking, nombre="06_ranking_predictores"):
    """
    Que tan bien predice cada candidato el valor de dentro de 24 horas.

    Recibe una serie de pandas con el nombre del candidato en el indice y la
    correlacion como valor.
    """
    estilo()
    r = ranking.reindex(ranking.abs().sort_values().index)

    fig, ax = plt.subplots(figsize=(9, 0.42 * len(r) + 1.2))
    ax.barh(r.index, r.values, color=[AZUL if v >= 0 else NARANJA for v in r.values],
            height=0.62)
    ax.axvline(0, color=TINTA_SUAVE, linewidth=0.8)
    ax.set_xlabel("correlacion con el benceno de dentro de 24 horas")
    ax.set_title("Que sirve para predecir, usando solo lo que se sabe hoy")
    ax.grid(axis="x")

    for y, valor in enumerate(r.values):
        desfase = 4 if valor >= 0 else -4
        ax.text(valor + (0.012 if valor >= 0 else -0.012), y, f"{valor:.2f}",
                va="center", ha="left" if valor >= 0 else "right",
                fontsize=9, color=TINTA)

    # Aire a los lados para que las etiquetas no toquen los nombres del eje
    ax.set_xlim(min(0, r.min() * 1.75), max(0, r.max() * 1.22))
    return _guardar(fig, nombre)


def comparacion_tramos(df, columnas=None, nombre="07_comparacion_tramos"):
    """
    Como cambia el promedio de cada variable de un tramo al siguiente.

    Un grafico por variable, porque tienen unidades distintas. Nunca dos ejes
    en el mismo grafico.
    """
    estilo()
    columnas = columnas or [config.TARGET, "T", "RH", "PT08.S4(NO2)"]

    d = df.set_index("datetime")
    tramos = {
        "TRAIN": (config.SPLIT_TRAIN_START, config.SPLIT_VALID_START),
        "VALID": (config.SPLIT_VALID_START, config.SPLIT_BATCH1_START),
        "BATCH 1": (config.SPLIT_BATCH1_START, config.SPLIT_BATCH2_START),
        "BATCH 2": (config.SPLIT_BATCH2_START, config.SPLIT_BATCH3_START),
        "BATCH 3": (config.SPLIT_BATCH3_START, "2005-12-31"),
    }

    fig, ejes = plt.subplots(1, len(columnas), figsize=(3.1 * len(columnas), 3.2))
    if len(columnas) == 1:
        ejes = [ejes]

    for eje, columna in zip(ejes, columnas):
        medias = [d.loc[(d.index >= a) & (d.index < b), columna].mean()
                  for a, b in tramos.values()]
        eje.plot(list(tramos), medias, color=AZUL, linewidth=2,
                 marker="o", markersize=6, markeredgecolor="white")
        eje.set_title(columna)
        eje.grid(axis="y")
        eje.tick_params(axis="x", rotation=55, labelsize=8)
        eje.margins(y=0.18)

        # Solo se etiqueta el primer y el ultimo tramo, que es la comparacion
        # que importa. La etiqueta se corre en sentido contrario a la pendiente
        # para no quedar encima de la linea.
        baja = medias[-1] < medias[0]
        eje.annotate(f"{medias[0]:.1f}", (0, medias[0]), textcoords="offset points",
                     xytext=(4, 8 if baja else -14), fontsize=9, color=TINTA, ha="left")
        eje.annotate(f"{medias[-1]:.1f}", (len(medias) - 1, medias[-1]),
                     textcoords="offset points", xytext=(-4, -14 if baja else 8),
                     fontsize=9, color=TINTA, ha="right")

    fig.suptitle("Los datos de produccion no se parecen a los de entrenamiento",
                 fontsize=12, color=TINTA)
    fig.tight_layout()
    return _guardar(fig, nombre)

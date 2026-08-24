"""
Monitoreo completo: corre todo y escribe el reporte.

Junta las tres dimensiones que pide la seccion N y las secciones O y Q:

    N2  Data Monitoring   - PSI, KS, Wasserstein y Jensen-Shannon por lote
    N3  Model Monitoring   - MAE y RMSE a lo largo del tiempo
    O   Simulacion         - REFERENCE contra los tres lotes de produccion
    Q   Reentrenamiento    - la decision, con su motivo escrito

La dimension que falta, N1 (System Monitoring), esta en la API: se ve en
GET /metrics y en las lineas del log de cada peticion.

Deja el resultado en reports/monitoreo.md y los graficos en reports/figuras/.

Se ejecuta asi:

    python -m src.monitoring.run_monitoring
"""

import json
import sys

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd

from src import config
from src.features.build_features import columnas_de_entrada, dividir_por_fecha
from src.logger import get_logger
from src.monitoring import drift, model_metrics, reentrenamiento
from src.monitoring import plots as graficos
from src.validation.diagnose import md_tabla

log = get_logger(__name__)

REPORTE = config.REPORTS_DIR / "monitoreo.md"


def cargar_modelo():
    """El mismo modelo que sirve la API."""
    from src.api.modelo import Modelo
    m = Modelo()
    if not m.cargar():
        raise RuntimeError("No se pudo cargar el modelo. Corra el entrenamiento.")
    return m


def main():
    log.info("=" * 62)
    log.info("MONITOREO")
    log.info("=" * 62)

    if not config.FEATURES_FILE.exists():
        log.error("No existe %s. Corra primero la construccion de variables.",
                  config.FEATURES_FILE)
        return 1

    modelo = cargar_modelo()
    log.info("Modelo: %s version %s (%s)",
             config.MODELO_REGISTRADO, modelo.version, modelo.algoritmo)

    tabla = pd.read_parquet(config.FEATURES_FILE)
    columnas = columnas_de_entrada(tabla)
    tramos = dividir_por_fecha(tabla)

    # REFERENCE es lo que el modelo conoce: entrenamiento mas validacion
    referencia = pd.concat([tramos["train"], tramos["validation"]], ignore_index=True)
    lotes = ["batch1", "batch2", "batch3"]

    log.info("Referencia: %s filas (%s a %s)", len(referencia),
             referencia["datetime"].min(), referencia["datetime"].max())

    # --- N2: cambios en los datos ---------------------------------------
    tablas_drift = {}
    resumenes = {}

    for lote in lotes:
        parte = tramos[lote]
        if len(parte) == 0:
            continue
        t = drift.comparar_lote(referencia, parte, columnas)
        r = drift.resumen_del_lote(t)
        drift.registrar(lote, t, r)
        tablas_drift[lote] = t
        resumenes[lote] = r

    # --- N3: desempeño del modelo ---------------------------------------
    desempeno = model_metrics.desempeno_por_lote(modelo.pipeline, tramos, columnas)
    model_metrics.registrar(desempeno)

    ventanas = model_metrics.desempeno_por_ventana(
        modelo.pipeline,
        pd.concat([tramos[l] for l in ["validation"] + lotes], ignore_index=True),
        columnas, dias=7,
    )

    # --- Q: reentrenar o no ---------------------------------------------
    decisiones = reentrenamiento.evaluar_lotes(resumenes, desempeno)
    reentrenamiento.registrar(decisiones)

    # --- Graficos --------------------------------------------------------
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    graficos.psi_por_lote(tablas_drift)
    graficos.drift_contra_desempeno(resumenes, desempeno)
    graficos.error_en_el_tiempo(ventanas)
    graficos.distribucion_referencia_vs_lotes(referencia, tramos, lotes,
                                              "T_lag24")

    # --- Reporte ---------------------------------------------------------
    escribir_reporte(referencia, tramos, lotes, tablas_drift, resumenes,
                     desempeno, ventanas, decisiones, modelo)

    log.info("Monitoreo terminado. Reporte en %s", REPORTE)
    return 0


def escribir_reporte(referencia, tramos, lotes, tablas_drift, resumenes,
                     desempeno, ventanas, decisiones, modelo):
    partes = [
        "# Reporte de monitoreo",
        "",
        "Generado por `python -m src.monitoring.run_monitoring`.",
        "",
        f"- Modelo: `{config.MODELO_REGISTRADO}` version {modelo.version} "
        f"({modelo.algoritmo})",
        f"- Referencia: {len(referencia)} filas, de {referencia['datetime'].min()} "
        f"a {referencia['datetime'].max()}",
        f"- Umbrales de PSI: aviso desde {config.PSI_WARNING}, "
        f"alerta desde {config.PSI_ALERT}",
        f"- Limite de degradacion: {config.DEGRADACION_MAXIMA*100:.0f}% de MAE",
        "",
        "## 1. Las tres dimensiones del monitoreo",
        "",
        "| Dimension | Que vigila | Donde esta |",
        "|---|---|---|",
        "| System (N1) | latencia, throughput, errores, disponibilidad | "
        "`GET /metrics` de la API y `logs/pipeline.log` |",
        "| Data (N2) | que las distribuciones no cambien | este reporte, seccion 2 |",
        "| Model (N3) | que el pronostico siga acertando | este reporte, seccion 3 |",
        "",
        "## 2. Cambios en los datos (Data Monitoring)",
        "",
        "Se comparan las distribuciones de cada variable en el periodo de",
        "referencia contra cada lote de produccion. Cuatro medidas distintas,",
        "porque cada una mira algo diferente:",
        "",
        "- **PSI**: parte la variable en diez tramos y compara los porcentajes. "
        "Es la que usamos para decidir.",
        "- **Kolmogorov-Smirnov**: la mayor distancia entre las curvas acumuladas. "
        "Ojo con su p-valor: con miles de filas casi todo sale significativo.",
        "- **Wasserstein**: cuanto habria que mover los datos, en las unidades de "
        "la variable.",
        "- **Jensen-Shannon**: que tan distintas son, de 0 a 1.",
        "",
    ]

    for lote in lotes:
        if lote not in tablas_drift:
            continue
        r = resumenes[lote]
        partes += [
            f"### {lote}",
            "",
            f"- Estado: **{r['estado']}**",
            f"- PSI mas alto: {r['psi_maximo']:.3f} en `{r['variable_mas_cambiada']}`",
            f"- Variables en alerta: {r['variables_en_alerta'] or 'ninguna'}",
            f"- Variables en aviso: {r['variables_en_aviso'] or 'ninguna'}",
            "",
            md_tabla(tablas_drift[lote]),
            "",
        ]

    partes += [
        "![PSI por lote](figuras/08_psi_por_lote.png)",
        "",
        "![Distribucion de la temperatura](figuras/11_distribucion_por_lote.png)",
        "",
        "## 3. Desempeño del modelo (Model Monitoring)",
        "",
        "Para un problema de pronostico las metricas que corresponden son MAE y",
        "RMSE seguidas en el tiempo. La columna `degradacion` compara contra el",
        "desempeño en validacion, que es con el que se aprobo el modelo.",
        "",
        md_tabla(desempeno),
        "",
        "![Error en el tiempo](figuras/10_error_en_el_tiempo.png)",
        "",
        "Una aclaracion que vale para la defensa: esto solo se puede calcular",
        "cuando ya se sabe lo que de verdad paso. Con un horizonte de 24 horas,",
        "el error de un pronostico recien se puede medir un dia despues. Mientras",
        "tanto, lo unico disponible es el monitoreo de datos. Por eso los dos son",
        "necesarios y ninguno reemplaza al otro.",
        "",
        "## 4. Drift no es lo mismo que degradacion",
        "",
        "Este es el hallazgo mas importante del monitoreo, y responde",
        "directamente la pregunta de la seccion Q del enunciado.",
        "",
        "| Lote | PSI maximo | Degradacion del MAE | Decision |",
        "|---|---|---|---|",
    ]

    for d in decisiones:
        partes.append(
            f"| {d['lote']} | {d.get('psi_maximo', 0):.3f} | "
            f"{(d.get('degradacion') or 0)*100:+.1f}% | **{d['decision']}** |"
        )

    partes += [
        "",
        "![Drift contra desempeño](figuras/09_drift_vs_desempeno.png)",
        "",
        "**El lote 3 tiene un drift enorme y el modelo anda mejor que en**",
        "**validacion.** Si el disparador mirara solo el PSI, habriamos",
        "reentrenado un modelo que estaba funcionando bien.",
        "",
        "Por que puede pasar:",
        "",
        "1. El modelo aprendio la **relacion** entre las variables, no sus valores.",
        "   Si aprendio que con temperatura baja hay menos benceno, un invierno",
        "   frio entra dentro de lo que ya sabe, aunque la distribucion de",
        "   temperatura se haya movido muchisimo.",
        "2. El drift puede estar en variables que al modelo casi no le importan.",
        "3. Y al reves tambien pasa: un modelo se puede degradar sin drift ninguno,",
        "   si cambia la relacion entre las variables y lo que se quiere predecir.",
        "   Eso se llama concept drift y el PSI no lo ve.",
        "",
        "## 5. Cuando reentrenar",
        "",
        "```",
        f"SI   PSI maximo >= {config.PSI_ALERT}",
        f"Y    degradacion del MAE > {config.DEGRADACION_MAXIMA*100:.0f}%",
        f"Y    el lote trae al menos {config.MIN_FILAS_PARA_DECIDIR} filas",
        "ENTONCES  reentrenar",
        "```",
        "",
        "Las cuatro respuestas posibles:",
        "",
        "| Drift | Degradacion | Decision | Por que |",
        "|---|---|---|---|",
        "| si | si | **REENTRENAR** | cambiaron los datos y el modelo lo sufrio |",
        "| si | no | **VIGILAR** | cambiaron los datos pero el modelo aguanta |",
        "| no | si | **REVISAR_DATOS** | algo pasa que el PSI no ve: concept drift, "
        "calidad o un periodo raro |",
        "| no | no | **TODO_BIEN** | seguir midiendo |",
        "",
        "Decisiones de esta corrida:",
        "",
    ]

    for d in decisiones:
        partes.append(f"- **{d['lote']}: {d['decision']}** — {d['motivo']}")

    partes += [
        "",
        "## 6. Sobre los umbrales",
        "",
        f"Los cortes del PSI ({config.PSI_WARNING} y {config.PSI_ALERT}) son los",
        "que se usan habitualmente desde los modelos de riesgo crediticio. **No son**",
        "**leyes universales**, y el propio enunciado pide no tratarlos como tales.",
        "",
        "En nuestro caso separan bien lo que vimos: las variables de calendario",
        "quedan en cero (y tiene que ser asi, la distribucion de horas y dias no",
        "cambia entre periodos), los rezagos del benceno quedan en la zona de aviso,",
        "y las ambientales se van muy por encima de la alerta por el cambio de",
        "estacion.",
        "",
        "Que las variables de calendario den PSI cercano a cero es la comprobacion",
        "de que el calculo esta bien hecho: si dieran alto, algo estaria mal.",
        "",
        "El limite de degradacion del 25% lo escogimos nosotras. Es un punto de",
        "partida razonable que habria que ajustar viendo cuanto le cuesta al negocio",
        "un error de pronostico.",
        "",
    ]

    REPORTE.write_text("\n".join(partes), encoding="utf-8")

    resumen_json = {
        "modelo": {"nombre": config.MODELO_REGISTRADO, "version": modelo.version,
                   "algoritmo": modelo.algoritmo},
        "umbrales": {"psi_warning": config.PSI_WARNING,
                     "psi_alert": config.PSI_ALERT,
                     "degradacion_maxima": config.DEGRADACION_MAXIMA},
        "lotes": {lote: {"drift": resumenes[lote]} for lote in resumenes},
        "decisiones": decisiones,
    }
    (config.REPORTS_DIR / "monitoreo.json").write_text(
        json.dumps(resumen_json, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

"""
Entrenamiento, registro en MLflow y seleccion del modelo.

Que hace, en orden:

1. Entrena el baseline y tres modelos mas, buscando hiperparametros con
   TimeSeriesSplit (que respeta el orden del tiempo).
2. Deja cada intento registrado en MLflow: parametros, metricas, graficos y el
   modelo. Todo lo que pide la seccion I.
3. Escoge uno con criterios explicitos, no "el que dio mejor".
4. Lo registra en el Model Registry y le pone el alias de produccion.

Se ejecuta asi:

    python -m src.training.train

Y para ver los resultados:

    mlflow ui --backend-store-uri ./mlruns
"""

import json
import sys
import tempfile
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # sin ventana grafica, solo archivos

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from src import config
from src.features.build_features import columnas_de_entrada, dividir_por_fecha
from src.ingestion.ingest import hash_archivo
from src.logger import get_logger
from src.training import evaluate, models

log = get_logger(__name__)


def preparar_mlflow():
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT)
    log.info("MLflow apuntando a %s", config.MLFLOW_TRACKING_URI)
    log.info("Experimento: %s", config.MLFLOW_EXPERIMENT)


def version_de_datos():
    """
    La huella del archivo crudo.

    Es lo que permite responder la pregunta de la seccion I: exactamente que
    datos produjeron este modelo.
    """
    if config.RAW_FILE.exists():
        return hash_archivo(config.RAW_FILE)
    return "desconocido"


def entrenar_uno(nombre, receta, tramos, entradas, data_version):
    """Entrena un modelo y lo deja registrado como un run de MLflow."""
    log.info("-" * 62)
    log.info("MODELO: %s  (%s)", nombre, receta["nota"])

    train, valid = tramos["train"], tramos["validation"]
    X_tr, y_tr = train[entradas], train["objetivo"]
    X_va, y_va = valid[entradas], valid["objetivo"]

    pipeline = models.armar_pipeline(receta)

    with mlflow.start_run(run_name=nombre) as run:
        arranque = time.perf_counter()

        # --- Busqueda de hiperparametros ---------------------------------
        if receta["rejilla"]:
            # TimeSeriesSplit y no KFold: cada corte entrena con el pasado y
            # prueba con el futuro. Con KFold normal estariamos entrenando con
            # datos posteriores a los que evaluamos.
            cv = TimeSeriesSplit(n_splits=4)
            busqueda = GridSearchCV(
                pipeline, receta["rejilla"], cv=cv,
                scoring="neg_mean_absolute_error", n_jobs=-1,
            )
            busqueda.fit(X_tr, y_tr)
            pipeline = busqueda.best_estimator_
            mejores = busqueda.best_params_
            log.info("Mejores hiperparametros: %s", mejores)
            mlflow.log_metric("cv_mae_log", -busqueda.best_score_)
        else:
            pipeline.fit(X_tr, y_tr)
            mejores = {}

        segundos = time.perf_counter() - arranque

        # --- Parametros (lo que pide la seccion I) ------------------------
        mlflow.log_params({
            "algorithm": nombre,
            "feature_set": f"v1_{len(entradas)}_variables",
            "random_seed": config.RANDOM_SEED,
            "data_version": data_version,
            "horizonte_horas": config.FORECAST_HORIZON,
            "target": config.TARGET,
            "target_en_log": config.USAR_LOG_TARGET,
            "filas_train": len(train),
            "filas_validation": len(valid),
            "rezagos": str(config.LAGS_TARGET),
            "ventanas_moviles": str(config.VENTANAS_MOVILES),
        })
        for clave, valor in mejores.items():
            mlflow.log_param(clave.replace("modelo__", "hp_"), valor)

        mlflow.set_tags({
            "grupo": "8",
            "integrantes": "Mayarling Martinez, Nicole Chavarria",
            "problema": "forecasting",
            "dataset": config.DATASET_NAME,
            "nota": receta["nota"],
        })

        # --- Metricas -----------------------------------------------------
        pred_tr = pipeline.predict(X_tr)
        pred_va = pipeline.predict(X_va)

        metricas = {}
        metricas.update(evaluate.calcular_metricas(y_tr, pred_tr, "train"))
        metricas.update(evaluate.calcular_metricas(y_va, pred_va, "validation"))

        # Los lotes de produccion tambien se miden aqui, para tener desde ya el
        # punto de partida contra el que comparar en el monitoreo.
        for lote in ["batch1", "batch2", "batch3"]:
            parte = tramos[lote]
            if len(parte):
                p = pipeline.predict(parte[entradas])
                metricas.update(evaluate.calcular_metricas(parte["objetivo"], p, lote))

        metricas["segundos_entrenamiento"] = segundos
        mlflow.log_metrics(metricas)

        log.info("train      %s", evaluate.formatear(
            {k: v for k, v in metricas.items() if k.startswith("train_")}))
        log.info("validation %s", evaluate.formatear(
            {k: v for k, v in metricas.items() if k.startswith("validation_")}))

        # --- Artefactos ---------------------------------------------------
        with tempfile.TemporaryDirectory() as carpeta:
            c = Path(carpeta)

            evaluate.grafico_residuos(y_va, pred_va, nombre, c / "residuos.png")
            evaluate.grafico_real_vs_predicho(y_va, pred_va, nombre,
                                              c / "real_vs_predicho.png")
            evaluate.grafico_serie(list(valid["datetime"]), np.asarray(y_va),
                                   pred_va, nombre, c / "serie.png")

            nombres_imp, valores_imp, metodo = models.importancias(
                pipeline, entradas, X_va, y_va)
            if nombres_imp:
                evaluate.grafico_importancias(
                    nombres_imp, valores_imp, f"{nombre} ({metodo})",
                    c / "importancias.png")
                mlflow.log_param("metodo_importancias", metodo)

            configuracion = {
                "modelo": nombre,
                "hiperparametros": {k: str(v) for k, v in mejores.items()},
                "variables": entradas,
                "target": config.TARGET,
                "horizonte_horas": config.FORECAST_HORIZON,
                "target_en_log": config.USAR_LOG_TARGET,
                "data_version": data_version,
                "random_seed": config.RANDOM_SEED,
                "cortes": {
                    "train": config.SPLIT_TRAIN_START,
                    "validation": config.SPLIT_VALID_START,
                    "batch1": config.SPLIT_BATCH1_START,
                    "batch2": config.SPLIT_BATCH2_START,
                    "batch3": config.SPLIT_BATCH3_START,
                },
            }
            (c / "configuracion.json").write_text(
                json.dumps(configuracion, indent=2, ensure_ascii=False), encoding="utf-8")

            mlflow.log_artifacts(str(c), artifact_path="evaluacion")

        # --- El modelo ----------------------------------------------------
        # La firma y el ejemplo hacen que MLflow guarde que columnas espera y
        # de que tipo. La API los usa para rechazar entradas mal formadas.
        firma = mlflow.models.infer_signature(X_va, pred_va)
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="modelo",
            signature=firma,
            input_example=X_va.head(3),
        )

        log.info("Run guardado: %s", run.info.run_id)

        return {
            "modelo": nombre,
            "run_id": run.info.run_id,
            "mae_train": metricas["train_mae"],
            "mae_validation": metricas["validation_mae"],
            "rmse_validation": metricas["validation_rmse"],
            "mape_validation": metricas["validation_mape"],
            "r2_validation": metricas["validation_r2"],
            "hiperparametros": mejores,
            "segundos": segundos,
        }


def escoger_modelo(resumen):
    """
    Aplica los criterios de la seccion J.

    No gana el de mejor numero: gana el mejor de entre los que cumplen las tres
    condiciones. Cada rechazo queda escrito, para poder explicarlo despues.
    """
    baseline = next((r for r in resumen if "baseline" in r["modelo"]), None)
    if baseline is None:
        raise RuntimeError("No hay baseline con que comparar")

    mae_baseline = baseline["mae_validation"]
    log.info("=" * 62)
    log.info("SELECCION DEL MODELO")
    log.info("=" * 62)
    log.info("Baseline (%s): MAE %.3f ug/m3", baseline["modelo"], mae_baseline)
    log.info("Criterios:")
    log.info("  1. mejorar el MAE del baseline en al menos %.0f%%",
             config.MEJORA_MINIMA_VS_BASELINE * 100)
    log.info("  2. el MAE de validacion no puede ser mas de %.0f%% peor que el de train",
             config.MAX_DEGRADACION_TRAIN_VALID * 100)
    log.info("  3. el MAE de validacion no puede pasar de %.1f ug/m3",
             config.MAE_MAXIMO_ACEPTABLE)

    aprobados = []
    for r in resumen:
        if "baseline" in r["modelo"]:
            continue

        mejora = 1 - r["mae_validation"] / mae_baseline
        degradacion = (r["mae_validation"] / r["mae_train"] - 1) if r["mae_train"] > 0 else 999

        fallos = []
        if mejora < config.MEJORA_MINIMA_VS_BASELINE:
            fallos.append(f"solo mejora {mejora*100:.1f}% al baseline")
        if degradacion > config.MAX_DEGRADACION_TRAIN_VALID:
            fallos.append(f"se degrada {degradacion*100:.1f}% de train a validation")
        if r["mae_validation"] > config.MAE_MAXIMO_ACEPTABLE:
            fallos.append(f"MAE {r['mae_validation']:.2f} pasa el techo")

        r["mejora_vs_baseline"] = mejora
        r["degradacion"] = degradacion

        if fallos:
            log.warning("  %-20s RECHAZADO: %s", r["modelo"], "; ".join(fallos))
        else:
            log.info("  %-20s APROBADO  (mejora %.1f%%, degradacion %.1f%%)",
                     r["modelo"], mejora * 100, degradacion * 100)
            aprobados.append(r)

    if not aprobados:
        log.error("Ningun modelo cumplio los criterios. No se registra nada.")
        return None

    ganador = min(aprobados, key=lambda r: r["mae_validation"])
    log.info("Gana %s con MAE %.3f ug/m3 en validacion",
             ganador["modelo"], ganador["mae_validation"])
    return ganador


def registrar(ganador):
    """
    Sube el modelo al Model Registry y le pone los alias.

    El ciclo del enunciado (Experiment -> Candidate -> Validation -> Production)
    queda representado asi:
      - Experiment : cada run del experimento
      - Candidate  : la version recien registrada, con alias 'candidato'
      - Validation : los criterios de escoger_modelo, anotados como tags
      - Production : alias 'produccion' sobre la version que paso
    """
    cliente = mlflow.MlflowClient()

    uri = f"runs:/{ganador['run_id']}/modelo"
    version = mlflow.register_model(uri, config.MODELO_REGISTRADO)
    log.info("Registrado %s version %s", config.MODELO_REGISTRADO, version.version)

    cliente.set_registered_model_alias(
        config.MODELO_REGISTRADO, config.ALIAS_CANDIDATO, version.version)
    log.info("Alias '%s' puesto en la version %s",
             config.ALIAS_CANDIDATO, version.version)

    # Las notas dejan por escrito por que este modelo y no otro
    cliente.set_model_version_tag(
        config.MODELO_REGISTRADO, version.version, "algoritmo", ganador["modelo"])
    cliente.set_model_version_tag(
        config.MODELO_REGISTRADO, version.version, "mae_validacion",
        f"{ganador['mae_validation']:.4f}")
    cliente.set_model_version_tag(
        config.MODELO_REGISTRADO, version.version, "mejora_vs_baseline",
        f"{ganador['mejora_vs_baseline']*100:.1f}%")
    cliente.set_model_version_tag(
        config.MODELO_REGISTRADO, version.version, "validado", "si")

    cliente.update_model_version(
        config.MODELO_REGISTRADO, version.version,
        description=(
            f"Modelo {ganador['modelo']} para pronosticar {config.TARGET} a "
            f"{config.FORECAST_HORIZON} horas. "
            f"MAE {ganador['mae_validation']:.2f} ug/m3 en validacion, "
            f"{ganador['mejora_vs_baseline']*100:.1f}% mejor que el baseline. "
            f"Grupo 8 - Mayarling Martinez y Nicole Chavarria."
        ),
    )

    cliente.set_registered_model_alias(
        config.MODELO_REGISTRADO, config.ALIAS_PRODUCCION, version.version)
    log.info("Alias '%s' puesto en la version %s. El modelo pasa a produccion.",
             config.ALIAS_PRODUCCION, version.version)

    return version.version


def exportar(ganador, version, entradas):
    """
    Deja una copia del modelo de produccion como archivos sueltos.

    Dentro de mlruns MLflow guarda rutas absolutas de esta maquina, y adentro
    de Docker esas rutas no existen. Esta copia es la que se mete en la imagen
    y funciona en cualquier lado.

    Ademas se escribe un json con la ficha del modelo, para que la API pueda
    decir que version esta sirviendo sin tener que abrir MLflow.
    """
    import shutil

    destino = config.MODELO_EXPORTADO_DIR
    if destino.exists():
        shutil.rmtree(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    modelo = mlflow.sklearn.load_model(f"runs:/{ganador['run_id']}/modelo")
    firma = mlflow.models.get_model_info(f"runs:/{ganador['run_id']}/modelo").signature
    mlflow.sklearn.save_model(modelo, str(destino), signature=firma)

    ficha = {
        "modelo_registrado": config.MODELO_REGISTRADO,
        "version": str(version),
        "algoritmo": ganador["modelo"],
        "run_id": ganador["run_id"],
        "target": config.TARGET,
        "horizonte_horas": config.FORECAST_HORIZON,
        "target_en_log": config.USAR_LOG_TARGET,
        "variables": entradas,
        "mae_validacion": round(ganador["mae_validation"], 4),
        "rmse_validacion": round(ganador["rmse_validation"], 4),
        "r2_validacion": round(ganador["r2_validation"], 4),
        "mejora_vs_baseline_pct": round(ganador["mejora_vs_baseline"] * 100, 1),
        "grupo": "8",
        "integrantes": ["Mayarling Martinez", "Nicole Chavarria"],
    }
    config.MODELO_EXPORTADO_META.write_text(
        json.dumps(ficha, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("Modelo exportado a %s", destino)
    log.info("Ficha del modelo en %s", config.MODELO_EXPORTADO_META)


def main():
    log.info("=" * 62)
    log.info("ENTRENAMIENTO")
    log.info("=" * 62)

    if not config.FEATURES_FILE.exists():
        log.error("No existe %s. Corra primero la construccion de variables.",
                  config.FEATURES_FILE)
        return 1

    preparar_mlflow()

    tabla = pd.read_parquet(config.FEATURES_FILE)
    entradas = columnas_de_entrada(tabla)
    tramos = dividir_por_fecha(tabla)
    data_version = version_de_datos()

    log.info("Variables: %s | data_version: %s", len(entradas), data_version)
    for nombre, parte in tramos.items():
        log.info("  %-11s %5d filas", nombre, len(parte))

    resumen = []
    for nombre, receta in models.catalogo().items():
        resumen.append(entrenar_uno(nombre, receta, tramos, entradas, data_version))

    # --- Tabla comparativa ------------------------------------------------
    log.info("=" * 62)
    log.info("RESULTADOS EN VALIDACION")
    log.info("=" * 62)
    log.info("%-22s %8s %8s %8s %8s", "modelo", "MAE", "RMSE", "MAPE", "R2")
    for r in sorted(resumen, key=lambda x: x["mae_validation"]):
        log.info("%-22s %8.3f %8.3f %7.1f%% %8.3f", r["modelo"],
                 r["mae_validation"], r["rmse_validation"],
                 r["mape_validation"], r["r2_validation"])

    ganador = escoger_modelo(resumen)
    if ganador is None:
        return 1

    # El grafico comparativo y la tabla van en un run aparte, para que quede
    # como resumen del experimento completo.
    with mlflow.start_run(run_name="comparacion_de_modelos"):
        with tempfile.TemporaryDirectory() as carpeta:
            c = Path(carpeta)
            evaluate.grafico_comparacion_modelos(resumen, c / "comparacion.png")
            pd.DataFrame(resumen).to_csv(c / "resumen.csv", index=False)
            (c / "criterios_de_seleccion.json").write_text(json.dumps({
                "mejora_minima_vs_baseline": config.MEJORA_MINIMA_VS_BASELINE,
                "max_degradacion_train_valid": config.MAX_DEGRADACION_TRAIN_VALID,
                "mae_maximo_aceptable": config.MAE_MAXIMO_ACEPTABLE,
                "ganador": ganador["modelo"],
                "run_id_ganador": ganador["run_id"],
            }, indent=2, ensure_ascii=False), encoding="utf-8")
            mlflow.log_artifacts(str(c), artifact_path="comparacion")
        mlflow.set_tag("tipo", "resumen del experimento")

    version = registrar(ganador)
    exportar(ganador, version, entradas)

    log.info("=" * 62)
    log.info("Modelo en produccion: %s v%s (%s)",
             config.MODELO_REGISTRADO, version, ganador["modelo"])
    log.info("Para ver los experimentos: mlflow ui --backend-store-uri ./mlruns")
    log.info("Entrenamiento terminado sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())

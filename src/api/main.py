"""
API de inferencia.

Levanta el modelo de produccion y lo deja disponible por HTTP.

Endpoints:
    GET  /              informacion basica
    GET  /health        si el servicio esta vivo y si el modelo cargo
    GET  /model-info    version, algoritmo, metricas y variables que espera
    POST /predict       un pronostico a partir del historial reciente
    POST /predict/batch varios pronosticos de una vez
    GET  /metrics       latencia, throughput, tasa de error y disponibilidad

Se levanta asi:

    uvicorn src.api.main:app --reload

Y la documentacion interactiva queda en http://127.0.0.1:8000/docs
"""

import time
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src import config
from src.api import schemas
from src.api.metricas import contadores
from src.api.modelo import modelo
from src.features.build_features import construir_features
from src.logger import get_logger

log = get_logger(__name__)

HORIZONTE_TEXTO = f"{config.FORECAST_HORIZON}h"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Carga el modelo una sola vez, al arrancar."""
    log.info("=" * 62)
    log.info("Arrancando la API de pronostico de benceno")
    log.info("=" * 62)
    modelo.cargar()
    if not modelo.cargado:
        log.error("La API arranca sin modelo. /predict va a responder 503.")
    yield
    log.info("Apagando la API")


app = FastAPI(
    title="Pronostico de benceno - Grupo 8",
    description=(
        "Pronostica la concentracion de benceno (C6H6) con 24 horas de "
        "anticipacion, a partir de las mediciones de las ultimas horas.\n\n"
        "Proyecto MLOps - Mayarling Martinez y Nicole Chavarria.\n\n"
        "Dataset Air Quality (UCI, id 360)."
    ),
    version="1.0.0",
    lifespan=ciclo_de_vida,
)


@app.middleware("http")
async def medir_cada_peticion(request: Request, call_next):
    """
    Cronometra cada peticion, la anota en las metricas y la deja en el log.

    Esta es la fuente de las cuatro metricas de la seccion N1. Cada linea del
    log trae metodo, ruta, codigo y milisegundos, asi que el monitoreo se puede
    reconstruir despues leyendo el archivo.
    """
    arranque = time.perf_counter()
    try:
        respuesta = await call_next(request)
        codigo = respuesta.status_code
    except Exception:
        codigo = 500
        milisegundos = (time.perf_counter() - arranque) * 1000
        contadores.anotar(request.url.path, milisegundos, codigo)
        log.exception("%s %s -> 500 en %.1f ms", request.method, request.url.path,
                      milisegundos)
        raise

    milisegundos = (time.perf_counter() - arranque) * 1000
    contadores.anotar(request.url.path, milisegundos, codigo)

    nivel = log.warning if codigo >= 400 else log.info
    nivel("%s %s -> %s en %.1f ms", request.method, request.url.path, codigo,
          milisegundos)

    respuesta.headers["X-Latencia-ms"] = f"{milisegundos:.1f}"
    return respuesta


# --------------------------------------------------------------------------
# Informacion
# --------------------------------------------------------------------------

@app.get("/", tags=["informacion"])
def inicio():
    return {
        "servicio": "Pronostico de benceno a 24 horas",
        "grupo": 8,
        "integrantes": ["Mayarling Martinez", "Nicole Chavarria"],
        "documentacion": "/docs",
        "estado": "/health",
    }


@app.get("/health", response_model=schemas.RespuestaSalud, tags=["informacion"])
def salud():
    """Para saber si el servicio esta vivo y si tiene modelo."""
    return schemas.RespuestaSalud(
        estado="ok" if modelo.cargado else "sin modelo",
        modelo_cargado=modelo.cargado,
        model_version=modelo.version if modelo.cargado else None,
        origen_del_modelo=modelo.origen,
        segundos_en_pie=round(time.time() - contadores.arranque, 1),
    )


@app.get("/model-info", response_model=schemas.RespuestaModelo, tags=["informacion"])
def informacion_del_modelo():
    """Que modelo esta sirviendo y con que numeros se aprobo."""
    if not modelo.cargado:
        raise HTTPException(status_code=503, detail="El modelo no esta cargado")

    return schemas.RespuestaModelo(
        model_version=modelo.version,
        algoritmo=modelo.algoritmo,
        target=config.TARGET,
        horizonte_horas=config.FORECAST_HORIZON,
        variables=modelo.variables(),
        horas_de_historial_necesarias=schemas.horas_minimas(),
        mae_validacion=modelo.ficha.get("mae_validacion"),
        rmse_validacion=modelo.ficha.get("rmse_validacion"),
        r2_validacion=modelo.ficha.get("r2_validacion"),
        origen_del_modelo=modelo.origen or "desconocido",
    )


@app.get("/metrics", response_model=schemas.RespuestaMetricas, tags=["monitoreo"])
def metricas_operativas():
    """Las cuatro metricas de sistema que pide la seccion N1."""
    return schemas.RespuestaMetricas(**contadores.resumen())


# --------------------------------------------------------------------------
# Pronostico
# --------------------------------------------------------------------------

def _a_dataframe(historial):
    """Pasa el historial recibido a la tabla que espera el pipeline."""
    filas = []
    for obs in historial:
        filas.append({
            "datetime": obs.fecha_hora,
            "CO(GT)": obs.co_gt,
            "PT08.S1(CO)": obs.pt08_s1,
            "C6H6(GT)": obs.c6h6_gt,
            "PT08.S2(NMHC)": obs.pt08_s2,
            "NOx(GT)": obs.nox_gt,
            "PT08.S3(NOx)": obs.pt08_s3,
            "NO2(GT)": obs.no2_gt,
            "PT08.S4(NO2)": obs.pt08_s4,
            "PT08.S5(O3)": obs.pt08_s5,
            "T": obs.temperatura,
            "RH": obs.humedad_relativa,
            "AH": obs.humedad_absoluta,
        })
    df = pd.DataFrame(filas)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.sort_values("datetime").reset_index(drop=True)


def _construir_variables(df):
    """
    Arma las variables con la MISMA funcion que uso el entrenamiento.

    Aqui esta el cumplimiento de la seccion H: no hay una copia de la logica
    para produccion. Es literalmente el mismo codigo, importado de
    src/features/build_features.py.
    """
    return construir_features(df, con_objetivo=False)


@app.post("/predict", response_model=schemas.RespuestaPronostico, tags=["pronostico"])
def predecir(peticion: schemas.PeticionPronostico):
    """
    Pronostica el benceno de dentro de 24 horas.

    Recibe las mediciones de las ultimas horas y devuelve un solo numero: cuanto
    benceno va a haber 24 horas despues de la ultima hora del historial.
    """
    arranque = time.perf_counter()

    if not modelo.cargado:
        raise HTTPException(status_code=503, detail="El modelo no esta cargado")

    minimo = schemas.horas_minimas()
    if len(peticion.historial) < minimo:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Hacen falta al menos {minimo} horas de historial y llegaron "
                f"{len(peticion.historial)}. La variable que mira mas atras es "
                f"el rezago de {max(config.LAGS_TARGET)} horas."
            ),
        )

    df = _a_dataframe(peticion.historial)
    variables = _construir_variables(df)

    columnas = modelo.variables()
    faltan = [c for c in columnas if c not in variables.columns]
    if faltan:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudieron construir las variables {faltan}",
        )

    ultima = variables.iloc[[-1]]
    if ultima[columnas].isna().any().any():
        vacias = [c for c in columnas if pd.isna(ultima[c].iloc[0])]
        raise HTTPException(
            status_code=422,
            detail=(
                "El historial tiene huecos y no se pudieron calcular todas las "
                f"variables. Quedaron vacias: {vacias}. Revise que las horas "
                "vengan seguidas y sin faltantes."
            ),
        )

    valor = float(modelo.predecir(ultima[columnas])[0])

    momento_base = pd.to_datetime(ultima["datetime"].iloc[0])
    momento_pronosticado = momento_base + pd.Timedelta(hours=config.FORECAST_HORIZON)
    milisegundos = (time.perf_counter() - arranque) * 1000

    log.info("Pronostico %.2f ug/m3 para %s (base %s, modelo v%s)",
             valor, momento_pronosticado, momento_base, modelo.version)

    return schemas.RespuestaPronostico(
        forecast=round(valor, 2),
        horizon=HORIZONTE_TEXTO,
        model_version=modelo.version,
        momento_base=momento_base,
        momento_pronosticado=momento_pronosticado,
        algoritmo=modelo.algoritmo,
        latencia_ms=round(milisegundos, 2),
    )


@app.post("/predict/batch", response_model=schemas.RespuestaLote, tags=["pronostico"])
def predecir_lote(peticion: schemas.PeticionPronostico):
    """
    Pronostica para todas las horas que tengan historial suficiente.

    Es el endpoint para la demo: se le manda un archivo de varios dias y
    devuelve un pronostico por cada hora que se pueda calcular.
    """
    arranque = time.perf_counter()

    if not modelo.cargado:
        raise HTTPException(status_code=503, detail="El modelo no esta cargado")

    df = _a_dataframe(peticion.historial)
    variables = _construir_variables(df)
    columnas = modelo.variables()

    completas = variables.dropna(subset=columnas)
    descartadas = len(variables) - len(completas)

    if completas.empty:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ninguna fila tiene historial suficiente. Se necesitan al menos "
                f"{schemas.horas_minimas()} horas seguidas y llegaron {len(df)}."
            ),
        )

    valores = modelo.predecir(completas[columnas])
    desfase = pd.Timedelta(hours=config.FORECAST_HORIZON)

    pronosticos = [
        {
            "momento_base": str(fecha),
            "momento_pronosticado": str(fecha + desfase),
            "forecast": round(float(v), 2),
        }
        for fecha, v in zip(pd.to_datetime(completas["datetime"]), valores)
    ]

    milisegundos = (time.perf_counter() - arranque) * 1000
    log.info("Lote de %s pronosticos en %.1f ms (%s filas descartadas)",
             len(pronosticos), milisegundos, descartadas)

    return schemas.RespuestaLote(
        model_version=modelo.version,
        horizon=HORIZONTE_TEXTO,
        cantidad=len(pronosticos),
        pronosticos=pronosticos,
        latencia_ms=round(milisegundos, 2),
        filas_descartadas=descartadas,
    )


# --------------------------------------------------------------------------

@app.exception_handler(Exception)
async def error_no_previsto(request: Request, exc: Exception):
    """
    Cualquier error que no hayamos previsto.

    Se responde 500 con un mensaje corto y el detalle completo queda en el log.
    No se devuelve el rastro del error al cliente: eso expone rutas y detalles
    internos del servidor.
    """
    log.exception("Error no previsto en %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno. Revise logs/pipeline.log"},
    )

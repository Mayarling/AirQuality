"""
Pruebas de la API.

Cubren lo que pide la seccion M:
  - peticion valida -> HTTP 200 -> respuesta con el esquema correcto
  - que sucede frente a una entrada invalida

Se corren asi:

    pytest tests/test_api.py -v
"""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src import config
from src.api.main import app
from src.api.schemas import horas_minimas


@pytest.fixture(scope="module")
def cliente():
    # El "with" dispara el arranque de la aplicacion, que es donde se carga el
    # modelo. Sin eso, /predict responderia 503 en todas las pruebas.
    with TestClient(app) as c:
        yield c


def observaciones(cantidad, desde="2005-01-01T00:00:00"):
    """Historial de mediciones inventado pero con forma de dia."""
    fechas = pd.date_range(desde, periods=cantidad, freq="h")
    generador = np.random.default_rng(config.RANDOM_SEED)
    base = 10 + 5 * np.sin(2 * np.pi * np.arange(cantidad) / 24)
    base = np.clip(base + generador.normal(0, 1.2, cantidad), 0.2, None)

    filas = []
    for i, fecha in enumerate(fechas):
        filas.append({
            "datetime": fecha.isoformat(),
            "CO(GT)": round(float(base[i] / 5), 2),
            "PT08.S1(CO)": round(float(base[i] * 95), 1),
            "C6H6(GT)": round(float(base[i]), 2),
            "PT08.S2(NMHC)": round(float(base[i] * 92), 1),
            "NOx(GT)": round(float(base[i] * 18), 1),
            "PT08.S3(NOx)": round(float(1200 - base[i] * 30), 1),
            "NO2(GT)": round(float(base[i] * 11), 1),
            "PT08.S4(NO2)": round(float(base[i] * 140), 1),
            "PT08.S5(O3)": round(float(base[i] * 88), 1),
            "T": round(float(12 + 4 * np.sin(2 * np.pi * i / 24)), 1),
            "RH": round(float(55 + 8 * np.cos(2 * np.pi * i / 24)), 1),
            "AH": 0.75,
        })
    return filas


# --------------------------------------------------------------------------
# El servicio responde
# --------------------------------------------------------------------------

def test_inicio(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert r.json()["grupo"] == 8


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["modelo_cargado"] is True
    assert cuerpo["estado"] == "ok"


def test_model_info(cliente):
    r = cliente.get("/model-info")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["target"] == config.TARGET
    assert cuerpo["horizonte_horas"] == config.FORECAST_HORIZON
    assert len(cuerpo["variables"]) == 18


# --------------------------------------------------------------------------
# Peticion valida -> 200 -> esquema correcto
# --------------------------------------------------------------------------

def test_prediccion_valida(cliente):
    r = cliente.post("/predict", json={"historial": observaciones(horas_minimas())})
    assert r.status_code == 200

    cuerpo = r.json()
    # Los tres campos que exige la seccion L para forecasting
    for campo in ["forecast", "horizon", "model_version"]:
        assert campo in cuerpo

    assert isinstance(cuerpo["forecast"], (int, float))
    assert cuerpo["horizon"] == f"{config.FORECAST_HORIZON}h"
    assert cuerpo["unidad"] == "ug/m3"


def test_el_pronostico_es_un_valor_posible(cliente):
    r = cliente.post("/predict", json={"historial": observaciones(200)})
    valor = r.json()["forecast"]
    assert valor >= 0, "el benceno no puede ser negativo"
    assert valor < 200, "un valor asi de alto no es creible"


def test_pronostica_24_horas_despues(cliente):
    r = cliente.post("/predict", json={"historial": observaciones(horas_minimas())})
    cuerpo = r.json()
    base = pd.Timestamp(cuerpo["momento_base"])
    pronosticado = pd.Timestamp(cuerpo["momento_pronosticado"])
    assert (pronosticado - base) == pd.Timedelta(hours=config.FORECAST_HORIZON)


def test_lote(cliente):
    r = cliente.post("/predict/batch", json={"historial": observaciones(200)})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["cantidad"] > 0
    assert len(cuerpo["pronosticos"]) == cuerpo["cantidad"]
    assert cuerpo["filas_descartadas"] == 200 - cuerpo["cantidad"]


# --------------------------------------------------------------------------
# Entradas invalidas
# --------------------------------------------------------------------------

def test_historial_muy_corto(cliente):
    """Con pocas horas no se pueden calcular los rezagos."""
    r = cliente.post("/predict", json={"historial": observaciones(10)})
    assert r.status_code == 422
    assert "historial" in r.json()["detail"].lower()


def test_historial_vacio(cliente):
    r = cliente.post("/predict", json={"historial": []})
    assert r.status_code == 422


def test_falta_el_campo_historial(cliente):
    r = cliente.post("/predict", json={})
    assert r.status_code == 422


def test_texto_donde_va_un_numero(cliente):
    """El caso del enunciado: age = 'treinta'."""
    filas = observaciones(horas_minimas())
    filas[0]["C6H6(GT)"] = "ocho coma cuatro"
    r = cliente.post("/predict", json={"historial": filas})
    assert r.status_code == 422


def test_fecha_invalida(cliente):
    filas = observaciones(horas_minimas())
    filas[0]["datetime"] = "no es una fecha"
    r = cliente.post("/predict", json={"historial": filas})
    assert r.status_code == 422


def test_historial_con_huecos(cliente):
    """Si faltan horas en medio, no se puede calcular el rezago correctamente."""
    filas = observaciones(horas_minimas())
    filas = filas[:20] + filas[60:]
    r = cliente.post("/predict", json={"historial": filas})
    assert r.status_code == 422


def test_json_mal_formado(cliente):
    r = cliente.post("/predict", content="{esto no es json",
                     headers={"Content-Type": "application/json"})
    assert r.status_code == 422


# --------------------------------------------------------------------------
# Metricas operativas
# --------------------------------------------------------------------------

def test_metricas(cliente):
    cliente.get("/health")
    r = cliente.get("/metrics")
    assert r.status_code == 200

    cuerpo = r.json()
    for campo in ["peticiones_totales", "tasa_de_error", "disponibilidad",
                  "throughput_por_minuto", "latencia_ms_p50", "latencia_ms_p95"]:
        assert campo in cuerpo

    assert cuerpo["peticiones_totales"] > 0
    assert 0 <= cuerpo["tasa_de_error"] <= 1
    assert 0 <= cuerpo["disponibilidad"] <= 1


def test_las_peticiones_traen_su_latencia(cliente):
    r = cliente.get("/health")
    assert "X-Latencia-ms" in r.headers
    assert float(r.headers["X-Latencia-ms"]) >= 0


# --------------------------------------------------------------------------
# El camino de carga que usa Docker
# --------------------------------------------------------------------------

def test_carga_sin_mlflow_da_el_mismo_resultado():
    """
    El contenedor no tiene MLflow instalado y carga models/produccion/model.pkl
    directamente. Esta prueba comprueba que ese camino da exactamente la misma
    prediccion que el camino normal.

    Si algun dia dejaran de coincidir, la API respondería una cosa en la maquina
    y otra distinta dentro de Docker, y nadie se enteraria.
    """
    from src.api.modelo import Modelo
    from src.features.build_features import columnas_de_entrada

    por_mlflow = Modelo()
    assert por_mlflow._desde_carpeta(), "no se pudo cargar con mlflow"

    por_pickle = Modelo()
    assert por_pickle._desde_pickle(), "no se pudo cargar el model.pkl"

    datos = pd.read_parquet(config.FEATURES_FILE)
    X = datos[columnas_de_entrada(datos)].head(50)

    np.testing.assert_allclose(
        por_mlflow.predecir(X), por_pickle.predecir(X), rtol=1e-10,
        err_msg="los dos caminos de carga dan resultados distintos",
    )

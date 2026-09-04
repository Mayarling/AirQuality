"""
Pruebas del monitoreo.

Lo que importa comprobar aqui es que las medidas de drift no mientan: que den
cero cuando no hay cambio y que suban cuando lo hay. Un detector de drift que
siempre alerta es tan inutil como uno que nunca alerta.
"""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.monitoring import drift, reentrenamiento


@pytest.fixture
def generador():
    return np.random.default_rng(config.RANDOM_SEED)


# --------------------------------------------------------------------------
# PSI
# --------------------------------------------------------------------------

def test_psi_cero_cuando_no_hay_cambio(generador):
    """Dos muestras de la misma distribucion tienen que dar un PSI bajito."""
    a = generador.normal(10, 2, 5000)
    b = generador.normal(10, 2, 5000)
    assert drift.psi(a, b) < config.PSI_WARNING


def test_psi_sube_cuando_la_media_se_corre(generador):
    """Si la distribucion se mueve, el PSI tiene que pasar la alerta."""
    a = generador.normal(10, 2, 5000)
    b = generador.normal(18, 2, 5000)
    assert drift.psi(a, b) > config.PSI_ALERT


def test_psi_crece_con_el_tamano_del_cambio(generador):
    """A mayor corrimiento, mayor PSI. Si no, el numero no sirve para ordenar."""
    a = generador.normal(10, 2, 5000)
    valores = [drift.psi(a, generador.normal(10 + d, 2, 5000)) for d in [0, 1, 3, 6]]
    assert valores == sorted(valores), f"el PSI no crece de forma ordenada: {valores}"


def test_psi_identico_es_cero():
    a = np.linspace(0, 100, 1000)
    assert drift.psi(a, a) == pytest.approx(0, abs=1e-6)


def test_psi_aguanta_una_variable_constante():
    """No debe reventar ni devolver infinito."""
    a = np.full(500, 7.0)
    b = np.full(500, 7.0)
    assert np.isfinite(drift.psi(a, b))


# --------------------------------------------------------------------------
# Las otras medidas
# --------------------------------------------------------------------------

def test_wasserstein_mide_el_corrimiento(generador):
    """Va en las unidades de la variable: si se corre 5, debe dar cerca de 5."""
    a = generador.normal(10, 1, 8000)
    b = generador.normal(15, 1, 8000)
    assert drift.wasserstein(a, b) == pytest.approx(5, abs=0.3)


def test_kolmogorov_detecta_la_diferencia(generador):
    a = generador.normal(10, 2, 3000)
    b = generador.normal(16, 2, 3000)
    estadistico, pvalor = drift.kolmogorov_smirnov(a, b)
    assert estadistico > 0.5
    assert pvalor < 0.05


def test_jensen_shannon_entre_cero_y_uno(generador):
    a = generador.normal(10, 2, 2000)
    b = generador.normal(30, 2, 2000)
    iguales = drift.jensen_shannon_distancia(a, a)
    distintas = drift.jensen_shannon_distancia(a, b)
    assert 0 <= iguales <= 1
    assert 0 <= distintas <= 1
    assert distintas > iguales


# --------------------------------------------------------------------------
# Semaforo
# --------------------------------------------------------------------------

@pytest.mark.parametrize("valor,esperado", [
    (0.02, drift.OK),
    (0.09, drift.OK),
    (0.10, drift.AVISO),
    (0.20, drift.AVISO),
    (0.25, drift.ALERTA),
    (5.00, drift.ALERTA),
])
def test_clasificacion_por_umbrales(valor, esperado):
    assert drift.clasificar(valor) == esperado


# --------------------------------------------------------------------------
# La decision de reentrenar
# --------------------------------------------------------------------------

def test_reentrena_solo_con_las_dos_condiciones():
    r = reentrenamiento.decidir(psi_maximo=1.5, degradacion=0.60, filas=1000)
    assert r["decision"] == reentrenamiento.REENTRENAR


def test_no_reentrena_solo_por_drift():
    """
    El caso del lote 3: los datos cambiaron muchisimo pero el modelo anda bien.

    Es la prueba que demuestra que entendemos que drift no es lo mismo que
    degradacion. Si esta prueba fallara, estariamos reentrenando modelos que
    funcionan.
    """
    r = reentrenamiento.decidir(psi_maximo=3.265, degradacion=-0.034, filas=1270)
    assert r["decision"] == reentrenamiento.VIGILAR
    assert r["hay_drift"] is True
    assert r["hay_degradacion"] is False


def test_avisa_cuando_se_degrada_sin_drift():
    """Puede ser concept drift, y el PSI no lo ve."""
    r = reentrenamiento.decidir(psi_maximo=0.05, degradacion=0.80, filas=1000)
    assert r["decision"] == reentrenamiento.REVISAR_DATOS


def test_todo_bien_cuando_no_pasa_nada():
    r = reentrenamiento.decidir(psi_maximo=0.03, degradacion=0.02, filas=1000)
    assert r["decision"] == reentrenamiento.TODO_BIEN


def test_no_decide_con_pocas_filas():
    """Con pocos datos cualquier metrica es ruido."""
    r = reentrenamiento.decidir(psi_maximo=9.9, degradacion=5.0, filas=20)
    assert r["decision"] == reentrenamiento.VIGILAR
    assert "muy pocas" in r["motivo"]


# --------------------------------------------------------------------------
# Comparacion de un lote entero
# --------------------------------------------------------------------------

def test_comparar_lote_ordena_por_psi(generador):
    n = 2000
    referencia = pd.DataFrame({
        "quieta": generador.normal(5, 1, n),
        "movida": generador.normal(5, 1, n),
        "datetime": pd.date_range("2004-01-01", periods=n, freq="h"),
    })
    produccion = pd.DataFrame({
        "quieta": generador.normal(5, 1, n),
        "movida": generador.normal(25, 1, n),
        "datetime": pd.date_range("2005-01-01", periods=n, freq="h"),
    })

    tabla = drift.comparar_lote(referencia, produccion, ["quieta", "movida"])
    assert tabla.iloc[0]["variable"] == "movida"
    assert tabla.iloc[0]["estado"] == drift.ALERTA
    assert tabla.iloc[1]["estado"] == drift.OK

    resumen = drift.resumen_del_lote(tabla)
    assert resumen["estado"] == drift.ALERTA
    assert resumen["variables_en_alerta"] == ["movida"]

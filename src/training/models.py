"""
Los modelos candidatos.

Cada uno viene con su rejilla de hiperparametros. La busqueda se hace con
TimeSeriesSplit, que respeta el orden del tiempo: entrena con lo viejo y prueba
con lo nuevo, nunca al reves.

El primero de la lista no es un modelo de verdad, es el baseline: repetir el
valor de hace 24 horas. Sirve como piso. Si un modelo con 18 variables y cien
arboles no le gana a eso, no vale la pena mantenerlo en produccion.
"""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config


class BaselinePersistencia(BaseEstimator, RegressorMixin):
    """
    El pronostico mas simple posible: manana a esta hora va a haber lo mismo
    que hoy a esta hora.

    Se escribe como un modelo de scikit-learn a proposito, para que pase por
    exactamente el mismo camino de evaluacion y de registro que los demas. Asi
    la comparacion es justa.
    """

    def __init__(self, columna="benceno_lag24"):
        self.columna = columna

    def fit(self, X, y=None):
        if self.columna not in X.columns:
            raise ValueError(f"El baseline necesita la columna {self.columna}")
        self.columnas_ = list(X.columns)
        return self

    def predict(self, X):
        return np.asarray(X[self.columna], dtype="float64")


def catalogo():
    """
    Devuelve los modelos a probar.

    Cada entrada trae:
      estimador  : el modelo sin entrenar
      rejilla    : hiperparametros a probar (vacia para el baseline)
      escala     : si necesita que las variables se pongan en la misma escala
    """
    semilla = config.RANDOM_SEED

    return {
        "baseline_persistencia": {
            "estimador": BaselinePersistencia(),
            "rejilla": {},
            "escala": False,
            "nota": "repite el valor de hace 24 horas",
        },
        "ridge": {
            "estimador": Ridge(random_state=None),
            "rejilla": {"modelo__alpha": [0.1, 1.0, 10.0, 50.0]},
            "escala": True,
            "nota": "regresion lineal con penalizacion",
        },
        "random_forest": {
            "estimador": RandomForestRegressor(random_state=semilla, n_jobs=-1),
            "rejilla": {
                "modelo__n_estimators": [200],
                "modelo__max_depth": [10, 18, None],
                "modelo__min_samples_leaf": [1, 5],
            },
            "escala": False,
            "nota": "bosque de arboles promediados",
        },
        "gradient_boosting": {
            "estimador": HistGradientBoostingRegressor(random_state=semilla),
            "rejilla": {
                "modelo__max_iter": [300],
                "modelo__learning_rate": [0.05, 0.1],
                "modelo__max_depth": [4, 8, None],
            },
            "escala": False,
            "nota": "arboles que corrigen el error del anterior",
        },
    }


def armar_pipeline(receta):
    """
    Envuelve el modelo en un Pipeline.

    Aunque el modelo no necesite escalado, va igual dentro de un Pipeline para
    que todos tengan la misma forma. Eso simplifica guardarlos en MLflow y
    cargarlos despues desde la API sin casos especiales.
    """
    pasos = []
    if receta["escala"]:
        pasos.append(("escalador", StandardScaler()))
    pasos.append(("modelo", receta["estimador"]))
    return Pipeline(pasos)


def importancias(pipeline, nombres, X=None, y=None):
    """
    Saca el peso de cada variable.

    Se intenta en tres pasos:

    1. feature_importances_ , que tienen los bosques.
    2. coef_ , que tienen los modelos lineales.
    3. Importancia por permutacion, que funciona con cualquier modelo: se
       revuelve una columna al azar y se mide cuanto empeora el error. Si
       empeora mucho, esa columna importaba.

    El tercer paso es el que salva al gradient boosting, que no ofrece ninguno
    de los dos atributos. Es mas lento pero mide lo que de verdad usa el
    modelo, no como esta construido por dentro.

    El baseline no tiene variables que pesar, y esta bien que devuelva nada.
    """
    from sklearn.inspection import permutation_importance

    modelo = pipeline.named_steps.get("modelo", pipeline)

    if hasattr(modelo, "feature_importances_"):
        return list(nombres), list(modelo.feature_importances_), "interna"
    if hasattr(modelo, "coef_"):
        return list(nombres), list(np.abs(modelo.coef_)), "coeficientes"

    if X is not None and y is not None:
        try:
            resultado = permutation_importance(
                pipeline, X, y, n_repeats=5,
                random_state=config.RANDOM_SEED,
                scoring="neg_mean_absolute_error", n_jobs=-1,
            )
            return list(nombres), list(resultado.importances_mean), "permutacion"
        except Exception:
            # El baseline llega aqui: no usa las columnas, asi que permutarlas
            # no cambia nada y el calculo no aporta.
            pass

    return None, None, None

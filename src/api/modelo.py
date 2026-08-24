"""
Carga del modelo que sirve la API.

El modelo se busca en cuatro lugares, en este orden:

1. La variable de entorno MODELO_URI, si esta puesta. Sirve para probar otra
   version sin tocar el codigo.
2. La carpeta models/produccion leida con MLflow.
3. El archivo models/produccion/model.pkl leido directamente. Este camino no
   necesita MLflow instalado, y es el que usa el contenedor de Docker.
4. El Model Registry por el alias de produccion. Es lo que se usa trabajando en
   la maquina de uno.

El orden no es capricho. Dentro de mlruns MLflow guarda las rutas absolutas de
la maquina donde se entreno; adentro de Docker esas rutas no existen. Y el
camino 3 permite que la imagen de Docker no tenga que instalar MLflow, que pesa
mas que todo lo demas junto.

MLflow se importa dentro de cada funcion y no arriba del archivo, justamente
para que la API funcione en un ambiente donde MLflow no este instalado.
"""

import json
import os

import numpy as np
import pandas as pd

from src import config
from src.logger import get_logger

log = get_logger(__name__)


class Modelo:
    """El modelo cargado, con su ficha."""

    def __init__(self):
        self.pipeline = None
        self.origen = None
        self.version = "desconocida"
        self.algoritmo = "desconocido"
        self.ficha = {}

    @property
    def cargado(self):
        return self.pipeline is not None

    def cargar(self):
        """Intenta los cuatro caminos en orden. Deja en el log cual funciono."""
        caminos = (self._desde_entorno, self._desde_carpeta,
                   self._desde_pickle, self._desde_registro)

        for intento in caminos:
            try:
                if intento():
                    log.info("Modelo cargado desde %s (version %s, %s)",
                             self.origen, self.version, self.algoritmo)
                    return True
            except Exception as e:
                log.warning("No se pudo cargar con %s: %s",
                            intento.__name__.lstrip("_"), e)

        log.error("No se pudo cargar el modelo por ningun camino")
        return False

    # ----------------------------------------------------------------

    def _desde_entorno(self):
        uri = os.environ.get("MODELO_URI")
        if not uri:
            return False
        import mlflow
        self.pipeline = mlflow.pyfunc.load_model(uri)
        self.origen = f"variable de entorno ({uri})"
        self._leer_ficha()
        return True

    def _desde_carpeta(self):
        if not config.MODELO_EXPORTADO_DIR.exists():
            return False
        import mlflow
        self.pipeline = mlflow.pyfunc.load_model(str(config.MODELO_EXPORTADO_DIR))
        self.origen = "carpeta exportada, leida con mlflow"
        self._leer_ficha()
        return True

    def _desde_pickle(self):
        """
        Carga el archivo del modelo sin pasar por MLflow.

        El pipeline guardado es un objeto normal de scikit-learn, asi que se
        puede abrir con cloudpickle. Gracias a esto la imagen de Docker no
        necesita MLflow y queda mucho mas liviana.
        """
        archivo = config.MODELO_EXPORTADO_DIR / "model.pkl"
        if not archivo.exists():
            return False

        import cloudpickle
        with open(archivo, "rb") as f:
            self.pipeline = cloudpickle.load(f)

        self.origen = "archivo model.pkl, sin mlflow"
        self._leer_ficha()
        return True

    def _desde_registro(self):
        import mlflow
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        uri = f"models:/{config.MODELO_REGISTRADO}@{config.ALIAS_PRODUCCION}"
        self.pipeline = mlflow.pyfunc.load_model(uri)
        self.origen = f"model registry ({uri})"

        cliente = mlflow.MlflowClient()
        version = cliente.get_model_version_by_alias(
            config.MODELO_REGISTRADO, config.ALIAS_PRODUCCION)
        self.version = str(version.version)
        self.algoritmo = version.tags.get("algoritmo", "desconocido")
        self._leer_ficha(solo_metricas=True)
        return True

    def _leer_ficha(self, solo_metricas=False):
        """La ficha que dejo el entrenamiento, con las metricas del modelo."""
        if not config.MODELO_EXPORTADO_META.exists():
            return
        self.ficha = json.loads(
            config.MODELO_EXPORTADO_META.read_text(encoding="utf-8"))
        if not solo_metricas:
            self.version = str(self.ficha.get("version", self.version))
            self.algoritmo = self.ficha.get("algoritmo", self.algoritmo)

    # ----------------------------------------------------------------

    def variables(self):
        """Los nombres de las columnas que el modelo espera, en orden."""
        if self.ficha.get("variables"):
            return list(self.ficha["variables"])

        # Sin ficha, se sacan de la firma que MLflow guardo con el modelo.
        # Solo existe si el modelo se cargo por alguno de los caminos de MLflow.
        try:
            entrada = self.pipeline.metadata.get_input_schema()
            return [c.name for c in entrada.inputs]
        except Exception:
            return []

    def predecir(self, X: pd.DataFrame):
        """
        Predice y devuelve el resultado en ug/m3.

        El modelo trabaja en logaritmo, asi que hay que deshacerlo antes de
        responder. Si no, la API devolveria numeros que no significan nada para
        quien la consume.
        """
        if not self.cargado:
            raise RuntimeError("El modelo no esta cargado")

        salida = np.asarray(self.pipeline.predict(X), dtype="float64")

        if config.USAR_LOG_TARGET:
            salida = np.expm1(salida)

        # El benceno no puede ser negativo. Si el modelo se pasa hacia abajo, se
        # recorta en cero en vez de devolver algo imposible.
        return np.clip(salida, 0.0, None)


# Una sola instancia para toda la aplicacion: cargar el modelo en cada peticion
# seria lentisimo.
modelo = Modelo()

"""
Que recibe y que devuelve la API.

Pydantic revisa cada campo antes de que el codigo lo toque. Si llega un texto
donde va un numero, o falta una columna, la peticion se rechaza con un 422 y un
mensaje que dice exactamente que estaba mal. Eso es lo que pide la seccion M
cuando habla de demostrar que pasa con una entrada invalida.

Los nombres de los campos en el JSON son los mismos del dataset original, con
sus puntos y parentesis: "PT08.S1(CO)", "C6H6(GT)". Asi el archivo que nos den
el dia de la demo se puede mandar tal cual, sin renombrar nada.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src import config


class Observacion(BaseModel):
    """Una hora de mediciones, tal como viene del dataset."""

    model_config = ConfigDict(populate_by_name=True)

    fecha_hora: datetime = Field(
        alias="datetime",
        description="Momento de la medicion, formato 2005-01-15T14:00:00",
    )
    co_gt: Optional[float] = Field(default=None, alias="CO(GT)")
    pt08_s1: Optional[float] = Field(default=None, alias="PT08.S1(CO)")
    c6h6_gt: Optional[float] = Field(default=None, alias="C6H6(GT)")
    pt08_s2: Optional[float] = Field(default=None, alias="PT08.S2(NMHC)")
    nox_gt: Optional[float] = Field(default=None, alias="NOx(GT)")
    pt08_s3: Optional[float] = Field(default=None, alias="PT08.S3(NOx)")
    no2_gt: Optional[float] = Field(default=None, alias="NO2(GT)")
    pt08_s4: Optional[float] = Field(default=None, alias="PT08.S4(NO2)")
    pt08_s5: Optional[float] = Field(default=None, alias="PT08.S5(O3)")
    temperatura: Optional[float] = Field(default=None, alias="T")
    humedad_relativa: Optional[float] = Field(default=None, alias="RH")
    humedad_absoluta: Optional[float] = Field(default=None, alias="AH")


class PeticionPronostico(BaseModel):
    """
    Las ultimas horas medidas.

    No se piden las 18 variables del modelo ya calculadas: se piden las
    mediciones crudas y la API construye las variables con la misma funcion que
    uso el entrenamiento. Esa es la forma de cumplir la seccion H, que prohibe
    tener una logica de variables en el entrenamiento y otra en produccion.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "historial": [
                    {"datetime": "2005-01-15T14:00:00", "CO(GT)": 2.1,
                     "PT08.S1(CO)": 1120.0, "C6H6(GT)": 8.4,
                     "PT08.S2(NMHC)": 940.0, "NOx(GT)": 180.0,
                     "PT08.S3(NOx)": 760.0, "NO2(GT)": 105.0,
                     "PT08.S4(NO2)": 1420.0, "PT08.S5(O3)": 980.0,
                     "T": 11.2, "RH": 55.4, "AH": 0.74},
                ]
            }
        }
    )

    historial: List[Observacion] = Field(
        min_length=1,
        description=(
            "Horas seguidas de mediciones, la mas reciente al final. "
            "Se necesitan al menos las suficientes para calcular el rezago mas "
            "largo."
        ),
    )


class RespuestaPronostico(BaseModel):
    """
    La respuesta, con el formato que pide la seccion L para forecasting.

    Los tres campos obligatorios son forecast, horizon y model_version. El resto
    es informacion util para el monitoreo.
    """

    # Sin esto pydantic reclama por el campo que empieza con "model_"
    model_config = ConfigDict(protected_namespaces=())

    forecast: float = Field(description="Benceno pronosticado en ug/m3")
    horizon: str = Field(description="Cuanto hacia adelante, por ejemplo 24h")
    model_version: str = Field(description="Version del modelo que respondio")

    unidad: str = "ug/m3"
    momento_base: datetime = Field(description="Ultima hora medida que se uso")
    momento_pronosticado: datetime = Field(description="Hora que se esta pronosticando")
    algoritmo: str
    latencia_ms: float


class RespuestaLote(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    horizon: str
    unidad: str = "ug/m3"
    cantidad: int
    pronosticos: List[dict]
    latencia_ms: float
    filas_descartadas: int = Field(
        description="Filas sin historial suficiente para calcular las variables"
    )


class RespuestaSalud(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    estado: str
    modelo_cargado: bool
    model_version: Optional[str] = None
    origen_del_modelo: Optional[str] = None
    segundos_en_pie: float


class RespuestaModelo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    algoritmo: str
    target: str
    horizonte_horas: int
    variables: List[str]
    horas_de_historial_necesarias: int
    mae_validacion: Optional[float] = None
    rmse_validacion: Optional[float] = None
    r2_validacion: Optional[float] = None
    origen_del_modelo: str


class RespuestaMetricas(BaseModel):
    """
    Las metricas operativas de la seccion N1: latencia, throughput, tasa de
    error y disponibilidad.
    """

    segundos_en_pie: float
    peticiones_totales: int
    peticiones_con_error: int
    tasa_de_error: float
    disponibilidad: float
    throughput_por_minuto: float
    latencia_ms_p50: Optional[float] = None
    latencia_ms_p95: Optional[float] = None
    latencia_ms_maxima: Optional[float] = None
    por_endpoint: dict


def horas_minimas():
    """
    Cuantas horas de historial hacen falta para calcular todas las variables.

    Sale de la variable que mira mas atras: el rezago de 168 horas, que medido
    desde el momento de predecir son 144 horas hacia atras. Mas la hora actual,
    145.
    """
    mayor_rezago = max(config.LAGS_TARGET) - config.FORECAST_HORIZON
    mayor_ventana = max(config.VENTANAS_MOVILES) - 1
    return max(mayor_rezago, mayor_ventana) + 1

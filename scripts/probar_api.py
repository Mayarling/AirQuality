"""
Prueba la API con datos reales del dataset.

Es el script de la demostracion en vivo. Toma un pedazo de los datos de
"produccion" (los ultimos meses, que el modelo nunca vio al entrenar), se los
manda a la API y compara el pronostico contra lo que de verdad paso.

Antes hay que tener la API levantada, en otra terminal:

    uvicorn src.api.main:app

    o, si esta en Docker:

    docker run -p 8000:8000 grupo8-mlops

Y despues:

    python scripts/probar_api.py
    python scripts/probar_api.py --lote batch1 --horas 300
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import config  # noqa: E402
from src.features.build_features import dividir_por_fecha  # noqa: E402

COLUMNAS = ["CO(GT)", "PT08.S1(CO)", "C6H6(GT)", "PT08.S2(NMHC)", "NOx(GT)",
            "PT08.S3(NOx)", "NO2(GT)", "PT08.S4(NO2)", "PT08.S5(O3)",
            "T", "RH", "AH"]


def titulo(texto):
    print()
    print("=" * 70)
    print(texto)
    print("=" * 70)


def a_observaciones(df):
    """Pasa el DataFrame al formato JSON que espera la API."""
    filas = []
    for _, fila in df.iterrows():
        obs = {"datetime": pd.Timestamp(fila["datetime"]).isoformat()}
        for columna in COLUMNAS:
            valor = fila.get(columna)
            obs[columna] = None if pd.isna(valor) else float(valor)
        filas.append(obs)
    return filas


def main():
    parser = argparse.ArgumentParser(description="Prueba la API con datos reales")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--lote", default="batch3",
                        choices=["validation", "batch1", "batch2", "batch3"])
    parser.add_argument("--horas", type=int, default=300,
                        help="cuantas horas del lote se mandan")
    args = parser.parse_args()

    # --- El servicio esta arriba? ---------------------------------------
    titulo("1. ESTADO DEL SERVICIO")
    try:
        salud = requests.get(f"{args.url}/health", timeout=10).json()
    except requests.exceptions.ConnectionError:
        print(f"No hay nadie escuchando en {args.url}")
        print("Levante la API primero:  uvicorn src.api.main:app")
        return 1

    for clave, valor in salud.items():
        print(f"  {clave:22s} {valor}")

    if not salud.get("modelo_cargado"):
        print("\nLa API esta arriba pero sin modelo. Corra el entrenamiento.")
        return 1

    # --- Que modelo esta sirviendo --------------------------------------
    titulo("2. MODELO EN PRODUCCION")
    info = requests.get(f"{args.url}/model-info", timeout=10).json()
    for clave in ["model_version", "algoritmo", "target", "horizonte_horas",
                  "mae_validacion", "r2_validacion", "origen_del_modelo",
                  "horas_de_historial_necesarias"]:
        print(f"  {clave:32s} {info.get(clave)}")

    # --- Datos reales ---------------------------------------------------
    if not config.PROCESSED_FILE.exists():
        print("\nNo existe la capa processed. Corra la limpieza primero.")
        return 1

    limpio = pd.read_parquet(config.PROCESSED_FILE)
    tabla = pd.read_parquet(config.FEATURES_FILE)
    fechas_lote = dividir_por_fecha(tabla)[args.lote]["datetime"]

    desde = fechas_lote.min() - pd.Timedelta(hours=info["horas_de_historial_necesarias"])
    hasta = fechas_lote.min() + pd.Timedelta(hours=args.horas)
    pedazo = limpio[(limpio["datetime"] >= desde) & (limpio["datetime"] < hasta)]

    titulo(f"3. PRONOSTICOS DE UNA HORA  (lote {args.lote})")
    historial = a_observaciones(pedazo)
    print(f"  Historial disponible: {len(historial)} horas, de "
          f"{pedazo['datetime'].min()} a {pedazo['datetime'].max()}")
    print()

    # Tres momentos repartidos y no uno solo. Con una sola hora, si toca un pico
    # aislado, el resultado no dice nada del modelo. En una serie de
    # contaminacion esos saltos existen y son impredecibles a 24 horas.
    minimo = info["horas_de_historial_necesarias"]
    cortes = [minimo, (minimo + len(historial)) // 2, len(historial)]
    cortes = sorted(set(c for c in cortes if minimo <= c <= len(historial)))

    print(f"  {'hora pronosticada':21s} {'real':>7s} {'pronostico':>11s} "
          f"{'error':>7s} {'ms':>7s}")

    respuesta = None
    for corte in cortes:
        r = requests.post(f"{args.url}/predict",
                          json={"historial": historial[:corte]}, timeout=60)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}: {r.json().get('detail')}")
            continue

        respuesta = r.json()
        momento = pd.Timestamp(respuesta["momento_pronosticado"])
        real = limpio.loc[limpio["datetime"] == momento, config.TARGET]

        if len(real) and pd.notna(real.iloc[0]):
            valor_real = float(real.iloc[0])
            print(f"  {str(momento):21s} {valor_real:7.2f} "
                  f"{respuesta['forecast']:11.2f} "
                  f"{abs(valor_real - respuesta['forecast']):7.2f} "
                  f"{respuesta['latencia_ms']:7.1f}")
        else:
            print(f"  {str(momento):21s} {'-':>7s} "
                  f"{respuesta['forecast']:11.2f} {'-':>7s} "
                  f"{respuesta['latencia_ms']:7.1f}")

    if respuesta:
        print("\n  Respuesta completa de la ultima peticion:")
        for clave, valor in respuesta.items():
            print(f"    {clave:22s} {valor}")

    # --- Un lote entero -------------------------------------------------
    titulo("4. UN LOTE COMPLETO")
    r = requests.post(f"{args.url}/predict/batch",
                      json={"historial": historial}, timeout=120)
    lote = r.json()
    print(f"  HTTP {r.status_code}")
    print(f"  Pronosticos      : {lote['cantidad']}")
    print(f"  Filas descartadas: {lote['filas_descartadas']} (sin historial suficiente)")
    print(f"  Latencia         : {lote['latencia_ms']} ms")

    predichos = pd.DataFrame(lote["pronosticos"])
    predichos["momento_pronosticado"] = pd.to_datetime(predichos["momento_pronosticado"])
    juntos = predichos.merge(
        limpio[["datetime", config.TARGET]],
        left_on="momento_pronosticado", right_on="datetime", how="inner",
    ).dropna()

    if len(juntos):
        error = (juntos[config.TARGET] - juntos["forecast"]).abs()
        print(f"\n  Comparado contra {len(juntos)} valores reales:")
        print(f"    MAE  {error.mean():.2f} ug/m3")
        print(f"    RMSE {np.sqrt(((juntos[config.TARGET] - juntos['forecast'])**2).mean()):.2f} ug/m3")
        print("\n  Primeras cinco horas:")
        print(f"    {'hora':21s} {'real':>7s} {'pronostico':>11s} {'error':>7s}")
        for _, f in juntos.head(5).iterrows():
            print(f"    {str(f['momento_pronosticado']):21s} "
                  f"{f[config.TARGET]:7.2f} {f['forecast']:11.2f} "
                  f"{abs(f[config.TARGET]-f['forecast']):7.2f}")

    # --- Entradas invalidas ---------------------------------------------
    titulo("5. QUE PASA CON ENTRADAS INVALIDAS")

    casos = [
        ("Historial demasiado corto", {"historial": historial[:5]}),
        ("Texto donde va un numero",
         {"historial": [{**h, "C6H6(GT)": "ocho"} if i == 0 else h
                        for i, h in enumerate(historial)]}),
        ("Falta el campo historial", {}),
        ("Historial vacio", {"historial": []}),
    ]

    for nombre, cuerpo in casos:
        r = requests.post(f"{args.url}/predict", json=cuerpo, timeout=30)
        detalle = r.json().get("detail")
        if isinstance(detalle, list) and detalle:
            detalle = detalle[0].get("msg", detalle[0])
        detalle = str(detalle)
        print(f"  {nombre:28s} -> HTTP {r.status_code}  {detalle[:70]}")

    # --- Metricas del servicio ------------------------------------------
    titulo("6. METRICAS OPERATIVAS DEL SERVICIO")
    metricas = requests.get(f"{args.url}/metrics", timeout=10).json()
    for clave in ["segundos_en_pie", "peticiones_totales", "peticiones_con_error",
                  "tasa_de_error", "disponibilidad", "throughput_por_minuto",
                  "latencia_ms_p50", "latencia_ms_p95", "latencia_ms_maxima"]:
        print(f"  {clave:24s} {metricas.get(clave)}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

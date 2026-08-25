# Presentación — Grupo #8

**Pronóstico de benceno a 24 horas** · Mayarling Martínez y Nicole Chavarría

Esta es la versión en texto de la presentación. El archivo para proyectar es
`presentacion/grupo8_mlops.pptx`, y se genera con:

```bash
node presentacion/armar_presentacion.js
```

Cada lámina lleva abajo **quién habla** y **qué decir**. Es lo mismo que está en
las notas del orador del PowerPoint.

---

## Lámina 1 — Portada

**Pronóstico de benceno a 24 horas**

Un sistema MLOps completo: de los datos crudos a un servicio vigilado.

Grupo #8 · Mayarling Martínez · Nicole Chavarría

| | |
|---|---|
| **2.905** | MAE en µg/m³ |
| **27.8%** | menos error que el baseline |
| **56** | pruebas automáticas |

> **Habla Mayarling.** Nos presentamos y decimos que el proyecto es un pipeline
> completo, no solo un modelo. Las tres cifras son el resumen: el error, cuánto
> le ganamos al modelo tonto, y las pruebas que lo respaldan.

---

## Lámina 2 — El problema

Pronosticar el benceno del aire con un día de anticipación.

- El benceno sale del tráfico y es cancerígeno. No hay un nivel seguro.
- Con 24 horas de aviso se puede restringir el tráfico, avisar a la población y proteger a la gente sensible.
- Con una hora de aviso no se organiza nada.

**La restricción que gobierna todo el diseño:** a la hora de hoy no podemos usar
ningún dato de las próximas 23 horas, porque en la vida real todavía no habrían
ocurrido.

**Cómo medimos:** MAE en µg/m³.

**Por qué el MAPE no sirve acá:** el lote 2 tiene el MAPE más alto (78.7%) y NO
el peor MAE.

**Metas fijadas antes de entrenar:** ganarle al menos 10% al baseline y no pasar
de 5 µg/m³.

> **Habla Mayarling.** Lo importante es que las metas las fijamos ANTES de
> entrenar, y que descartamos el MAPE con evidencia nuestra, no por gusto.

---

## Lámina 3 — Los datos

Air Quality de UCI · 9 357 horas seguidas · marzo 2004 a abril 2005.

1. **El archivo está mal formado para lectura directa.** Separador punto y coma,
   coma como decimal, columnas y filas vacías.
2. **Los faltantes vienen escritos como −200.** No son celdas vacías.
3. **Los huecos no están sueltos: son apagones del equipo.** 366 faltantes que en
   realidad son 16 periodos continuos sin medir; el más largo dura 76 horas.

Por eso interpolamos solo los huecos que caben enteros en 3 horas.

| | |
|---|---|
| **9 357** | horas en el archivo original |
| **16** | apagones, el mayor de 76 horas |
| **90.23%** | de `NMHC(GT)` son faltantes: se descarta la columna |

> **Habla Nicole.** El punto fuerte es el tercero: pasar de "hay 366 nulos" a
> "son 16 apagones" es lo que separa mirar una tabla de entender los datos. Si
> preguntan: la página de UCI dice que el periodo termina en febrero, pero el
> archivo llega hasta abril. Nos guiamos por el archivo.

---

## Lámina 4 — Arquitectura

El diagrama completo. Cada caja lleva debajo el archivo del repositorio que la
implementa.

> **Habla Mayarling.** Recorrer el camino de izquierda a derecha y de arriba
> abajo. Señalar las dos flechas naranjas punteadas: la que corta el pipeline si
> falla una regla dura, y la que vuelve al entrenamiento si la decisión dice
> REENTRENAR. Y decir que la simulación de daños usa LAS MISMAS reglas.

---

## Lámina 5 — Data Quality Gates

Nueve reglas que corren dos veces: a la entrada y a la salida de la limpieza.

**Duras — detienen el pipeline:** R01 esquema · R02 mínimo de filas ·
R03 timestamps sin repetir · R05 rangos físicos · R07 duplicados · R09 tipos de dato.

**Blandas — avisan y siguen:** R04 continuidad horaria · R06 huecos del target ·
R08 columnas constantes.

**Por qué la diferencia importa:** que falten unas horas sueltas es normal en un
equipo real y no justifica botar toda la corrida. Que aparezca una columna que no
existía, sí. Y si todas detuvieran el pipeline, la gente terminaría
desactivándolas.

> **Habla Nicole.** Insistir en que la separación dura/blanda es una decisión de
> diseño, no un descuido. Y en que las reglas corren dos veces, porque la segunda
> pasada comprueba que la limpieza no rompió nada.

---

## Lámina 6 — Sin leakage

Todos los rezagos se miden desde la hora que se quiere predecir, no desde ahora.

Para predecir `t+24`, el dato más reciente que existe es el de la hora `t`, que
respecto de `t+24` es un rezago de 24 horas. Un rezago de 1 hora usaría el dato
de `t+23`, que todavía no ocurrió.

```python
def _validar_rezago(rezago, horizonte):
    if rezago < horizonte:
        raise ErrorDeLeakage(
            f"Se pidio un rezago de {rezago} h "
            f"con un horizonte de {horizonte} h. ...")
```

Los comentarios no detienen a nadie. Por eso el proceso se cae solo.

**Excepción deliberada:** las variables de calendario sí se calculan sobre la
hora que se quiere predecir. Qué día va a ser mañana se sabe hoy.

**El caso extremo:** `PT08.S2(NMHC)` correlaciona 0.982 con el benceno. Usarlo
sin rezagar daría métricas espectaculares y un modelo inútil.

> **Habla Mayarling.** Esta es la lámina que hay que defender mejor. Una métrica
> muy buena puede ser una señal de alarma y no de éxito.

---

## Lámina 7 — Cuatro modelos, y cómo se escogió

| Modelo | MAE | RMSE | MAPE | R² |
|---|---|---|---|---|
| **gradient_boosting** | **2.905** | **4.430** | 33.4% | **0.648** |
| random_forest | 3.043 | 4.606 | 35.2% | 0.619 |
| ridge | 3.096 | 4.808 | 35.6% | 0.585 |
| baseline_persistencia | 4.021 | 6.070 | 53.4% | 0.338 |

**Los tres criterios, fijados antes de ver resultados:**

1. ganarle al baseline por al menos 10% de MAE
2. que validación no sea más de 60% peor que entrenamiento
3. que el MAE no pase de 5.0 µg/m³

**El criterio funcionó solo:** `random_forest` quedó RECHAZADO aunque su MAE era
mejor que el de `ridge`, porque se degradaba 68.4% de entrenamiento a validación.

> **Habla Mayarling.** El punto de venta es el rechazo de random_forest:
> demuestra que los criterios no son decoración. Si preguntan por ridge: se
> degrada solo 8.2% contra el 50.7% del ganador, y con más histórico sería un
> candidato serio.

---

## Lámina 8 — Trazabilidad con MLflow

| | |
|---|---|
| **15** | parámetros por corrida |
| **42** | métricas por corrida |
| **5** | artefactos por corrida |
| **2** | versiones registradas |

**El ciclo de vida:** `Experiment → candidato → produccion`, con alias y no con
stages, porque los stages quedaron obsoletos y lo avisa la propia interfaz.

**Dos cosas que valen doble:**

- Guardamos el md5 del archivo como `data_version`. De cualquier modelo se sabe
  con qué datos exactos se entrenó.
- Las dos versiones registradas tienen métricas idénticas hasta el último
  decimal: reproducibilidad demostrada, no prometida.

> **Habla Mayarling.** Mostrar la captura del Model Registry si hay tiempo.

---

## Lámina 9 — El servicio: API y contenedor

**La decisión importante:** la entrada no son las 18 variables ya calculadas,
sino las últimas 145 horas de mediciones. La API construye las variables por
dentro llamando a la misma función que usó el entrenamiento. Ese error tiene
nombre: *training-serving skew*.

**Los seis endpoints:** `/` · `/health` · `/model-info` · `/metrics` ·
`/predict` · `/predict/batch`

**Las cuatro decisiones de la imagen:**

- versión fija `python:3.12-slim`, nunca `latest`
- los requisitos se copian antes que el código, para aprovechar la caché
- solo se instala lo que la API necesita
- corre con un usuario sin privilegios

| | |
|---|---|
| 1.33 GB | con todo instalado |
| **865 MB** | solo lo que la API usa |

> **Habla Nicole.** Si preguntan por qué hizo falta exportar el modelo aparte:
> MLflow guarda rutas absolutas de Windows dentro de `mlruns`, y dentro del
> contenedor esas rutas no existen.

---

## Lámina 10 — Monitoreo en tres dimensiones

| Dimensión | Qué vigila | Dónde vive |
|---|---|---|
| **System** | latencia, throughput, errores, disponibilidad | `GET /metrics`, `logs/pipeline.log` |
| **Data** | que las distribuciones no cambien | `src/monitoring/drift.py` |
| **Model** | que el pronóstico siga acertando | `src/monitoring/model_metrics.py` |

**Cuatro medidas de drift:** PSI (la que decide) · Kolmogorov-Smirnov ·
Wasserstein · Jensen-Shannon.

**La comprobación de que el cálculo está bien:** las variables de calendario dan
PSI cercano a cero. Tiene que ser así. Los umbrales 0.10 y 0.25 vienen del riesgo
crediticio y no son leyes universales.

> **Habla Nicole.** Cuidado con el p-valor de Kolmogorov-Smirnov: con miles de
> filas casi cualquier diferencia sale significativa, por eso nunca decidimos con
> él solo.

---

## Lámina 11 — Drift no es lo mismo que degradación

| Lote | PSI máximo | Degradación del MAE |
|---|---|---|
| batch1 | 1.671 | +88.8% |
| batch2 | 6.175 | +51.1% |
| batch3 | 3.265 | **−3.4%** |

**El lote 3 tiene un PSI de 3.265 —trece veces el umbral de alerta— y el modelo
acierta un 3.4% MEJOR que en validación.**

Por qué puede pasar:

1. El modelo aprendió la relación entre las variables, no sus valores.
2. El drift puede estar en variables que al modelo casi no le importan.
3. Y al revés: se puede degradar sin drift ninguno. Eso es *concept drift* y el
   PSI no lo ve.

El de datos avisa temprano, apenas llega el lote. El de modelo confirma el daño,
pero con horizonte de 24 horas solo se puede medir un día después.

> **Habla Nicole.** Esta es LA lámina del proyecto y responde la pregunta de la
> sección Q del enunciado. Que quede claro que no es teoría: son nuestros tres
> lotes.

---

## Lámina 12 — Cuándo reentrenar

```
SI    el PSI más alto ≥ 0.25
Y     el MAE empeoró más de 25%
Y     el lote trae ≥ 200 filas
ENTONCES  reentrenar
```

| Drift | Degradación | Decisión |
|---|---|---|
| sí | sí | **REENTRENAR** |
| sí | no | **VIGILAR** |
| no | sí | **REVISAR_DATOS** |
| no | no | **TODO_BIEN** |

**Lo que decidió con nuestros lotes:** batch1 REENTRENAR · batch2 REENTRENAR ·
batch3 VIGILAR.

**El disparo no es automático, y es a propósito.** Con un solo modelo y trece
meses de historia, un reentrenamiento automático puede reemplazar un modelo bueno
por uno peor sin que nadie se entere.

> **Habla Nicole.** Si preguntan por qué no automatizamos: no es que no
> supiéramos hacerlo, es una decisión justificada por el tamaño del histórico.

---

## Lámina 13 — Pruebas y simulación de problemas

| | |
|---|---|
| **19** | pruebas de variables y anti-leakage |
| **17** | pruebas de la API |
| **20** | pruebas del monitoreo |

56 pruebas, todas pasando. La que más importa es
`test_no_reentrena_solo_por_drift`: reproduce el caso del lote 3 y falla si el
sistema decidiera reentrenar.

**Seis daños a una copia en memoria:** faltantes · duplicados · valor absurdo ·
tipo incorrecto · categoría desconocida · cambio de esquema.

Resultado: 6 de 7 reglas fallaron, pipeline bloqueado, dataset intacto (el md5
del archivo original es el mismo antes y después).

**Encontró un error real en nuestro código:** la regla R05 se caía cuando le
llegaba texto donde esperaba un número.

> **Habla Nicole.** Contar el error de R05 sin adornos: lo encontramos nosotras,
> lo corregimos y quedó la prueba. Eso vale más que decir que todo salió bien a
> la primera.

---

## Lámina 14 — Qué no hicimos, y qué haríamos con más tiempo

**Los límites:**

- Un solo lugar y un solo año.
- Trece meses es poco para una serie estacional: solo vimos un invierno.
- El umbral del 25% lo escogimos nosotras, no salió de datos del negocio.
- Los umbrales del PSI vienen prestados del riesgo crediticio.
- El modelo no explica pronósticos individuales.

**Lo que seguiría:**

- Conseguir más años de datos.
- Fijar el umbral de degradación con datos del negocio.
- Reentrenamiento automático, comparando el candidato contra el modelo vigente.
- Explicabilidad por pronóstico.
- Que las alertas salgan del log y le lleguen a alguien.

> **Habla Mayarling.** Esta lámina suele gustar: demuestra que sabemos dónde
> están los límites y que no estamos vendiendo el trabajo por más de lo que es.

---

## Lámina 15 — Demostración en vivo

| # | Paso | Comando |
|---|---|---|
| 1 | Raw Data | `python -m src.ingestion.ingest` |
| 2 | Validation | `python -m src.validation.diagnose` |
| 3 | Training | `python -m src.training.train` |
| 4 | MLflow | `mlflow ui` |
| 5 | Model Registry | alias `candidato` y `produccion` |
| 6 | Docker | `docker run -p 8000:8000 grupo8-mlops` |
| 7 | API Prediction | `python scripts/probar_api.py` |
| 8 | Monitoring | `python -m src.monitoring.run_monitoring` |
| 9 | Drift Alert | `python -m src.monitoring.contaminar` |

**Si nos pasan un lote que no hemos visto:** pasa por los mismos Data Quality
Gates. Si está bien, sale el pronóstico y el PSI contra la referencia. Si está
roto, el pipeline se detiene y dice qué regla falló y por qué.

> **Hablan las dos.** Tener el contenedor levantado ANTES de empezar. El guion
> completo está en `presentacion/guion_demo.md`.

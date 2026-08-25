# Guion de la demostración en vivo

Grupo #8 · 15 minutos · las dos con cámara encendida

Este archivo es para tenerlo abierto en una ventana aparte durante la defensa.

---

## Antes de empezar (hacerlo 20 minutos antes, no en el momento)

Esto es lo que más tiempo salva. Nada de esto se hace delante del profesor.

**Las dos:**

- [ ] Cerrar todo lo que no se vaya a usar: correo, chats, notificaciones.
- [ ] Poner el celular en silencio.
- [ ] Probar el micrófono y la cámara.

**Mayarling, que es la que comparte pantalla:**

- [ ] Abrir la terminal en la carpeta `AirQuality` con el entorno activado:

  ```
  .\.venv\Scripts\Activate.ps1
  ```

  Confirmar que aparece `(.venv)` en verde al principio de la línea.

- [ ] Levantar MLflow en **una terminal aparte**, porque queda ocupada:

  ```
  mlflow ui
  ```

  Y dejar abierta la pestaña `http://localhost:5000`.

- [ ] Levantar el contenedor **antes**, no en vivo:

  ```
  docker run -d -p 8000:8000 --name demo grupo8-mlops
  ```

  Esperar 30 segundos y comprobar:

  ```
  docker ps
  ```

  La columna STATUS tiene que decir **(healthy)**. Si dice *starting*, esperar.
  Si dice *unhealthy*, ver el apartado de problemas al final.

- [ ] Dejar abierta la pestaña `http://localhost:8000/docs`.

- [ ] Tener abiertos en pestañas del navegador:
  - el repositorio en GitHub
  - `reports/monitoreo.md` en PyCharm
  - `reports/figuras/12_arquitectura.png`

- [ ] Tener este archivo abierto en otra ventana.

**Si algo de esto no arranca, hay tiempo de arreglarlo. En vivo no.**

---

## Reparto y tiempos

| Min | Quién | Qué |
|---|---|---|
| 0–2 | Mayarling | Portada, problema, datos |
| 2–4 | Mayarling | Arquitectura |
| 4–6 | Nicole | Calidad de datos y limpieza |
| 6–8 | Mayarling | Sin leakage, modelos y MLflow |
| 8–10 | Nicole | API, Docker y monitoreo |
| 10–13 | Las dos | **Demostración en vivo** |
| 13–15 | Las dos | Cierre y preguntas |

Si van atrasadas, la lámina que se puede pasar rápido es la 14. **La 6 (leakage)
y la 11 (drift no es degradación) no se saltan nunca**: son las dos que más
valen.

---

## El recorrido de la demo (minutos 10 a 13)

El enunciado pide mostrar este camino. Va en este orden y sin saltarse pasos.

### 1 · Raw Data → Validation

```
python -m src.validation.diagnose
```

**Qué decir mientras corre:** "Acá se leen los datos crudos y pasan por las nueve
reglas de calidad. Fíjense en la línea de R04: avisa que la serie tiene huecos,
pero no detiene el proceso, porque es una regla blanda."

### 2 · Training

**No entrenar en vivo: tarda demasiado.** En vez de eso, mostrar el log:

```
Select-String -Path logs\pipeline.log -Pattern "RESULTADOS EN VALIDACION" -Context 0,7 | Select-Object -Last 1
```

**Qué decir:** "Estos son los cuatro modelos. Gana gradient_boosting con 2.905."

Y enseguida:

```
Select-String -Path logs\pipeline.log -Pattern "SELECCION DEL MODELO" -Context 0,15 | Select-Object -Last 1
```

**Qué decir:** "Y acá está lo interesante: random_forest quedó rechazado por el
criterio de sobreajuste, aunque su MAE era mejor que el de ridge."

### 3 · MLflow Experiment

Ir a la pestaña de MLflow, experimento `air-quality-benceno-24h`.

**Qué mostrar:** las corridas con sus métricas, ordenadas por `validation_mae`.

**Qué decir:** "Hay dos tandas porque entrenamos dos veces. Los números son
idénticos hasta el último decimal, y eso es la prueba de que el pipeline es
reproducible."

### 4 · Model Registry

Pestaña **Models** → `grupo8-benceno-24h`.

**Qué mostrar:** la Version 2 con los alias `candidato` y `produccion`, y sus
tags.

**Qué decir:** "Usamos alias y no stages porque los stages quedaron obsoletos.
El entrenamiento pone el alias `candidato` primero, comprueba los criterios, y
solo entonces mueve `produccion`."

### 5 · Docker Container

```
docker ps
```

**Qué decir:** "El contenedor ya está corriendo y Docker lo marca como healthy,
porque le pega a `/health` cada 30 segundos."

### 6 · API Prediction

```
python scripts/probar_api.py
```

**Qué decir:** "Le manda las últimas 145 horas de mediciones, no las variables
ya calculadas. La API las construye por dentro con la misma función del
entrenamiento."

Después mostrar en el navegador:

```
http://localhost:8000/metrics
```

**Qué decir:** "Este es el monitoreo de sistema: latencia, throughput y
disponibilidad."

### 7 · Monitoring

Abrir `reports/monitoreo.md` y mostrar la tabla de los tres lotes.

**Qué decir (Nicole):** "Miren el lote 3: el PSI es 3.265, trece veces el umbral
de alerta, y el modelo anda mejor que en validación. Por eso nuestro disparador
exige drift Y degradación, no una sola de las dos."

### 8 · Drift / Quality Alert

```
python -m src.monitoring.contaminar
```

**Qué decir:** "Le metemos seis daños a una copia en memoria de un lote y se lo
pasamos a las mismas reglas de calidad del pipeline."

Y al terminar, señalar las últimas líneas:

```
Reglas que fallaron : 6 de 7
Pipeline bloqueado  : si
Dataset intacto     : si
```

**Qué decir:** "Detecta, bloquea y registra. Y el archivo original queda con el
mismo md5 antes y después. Esta simulación nos encontró un error real en nuestra
propia regla R05."

---

## Si el profesor pasa un lote que no hemos visto

Puede pasar y está previsto. La respuesta corta: **entra por la misma puerta que
todo lo demás**.

**Paso 1 — Guardarlo donde va.** Que quede en `data/raw/` con su nombre.

**Paso 2 — Pasarlo por las reglas.** Si es un CSV con el mismo formato:

```
python -c "import pandas as pd; from src.validation.quality_gates import correr_gates; d=pd.read_csv(r'data/raw/NOMBRE.csv', sep=';', decimal=','); correr_gates(d, etapa='entrada', detener=False, min_filas=1)"
```

**Qué decir mientras corre:** "Antes de predecir nada, lo primero es preguntarse
si el dato sirve."

- **Si pasa las reglas:** seguir al paso 3.
- **Si falla una regla dura:** *ese es el resultado correcto y hay que decirlo con
  seguridad.* "El sistema lo rechazó y dice exactamente qué regla falló y por
  qué. Eso es justo lo que tiene que hacer: no queremos un pronóstico calculado
  sobre datos rotos."

**Paso 3 — Pedirle un pronóstico a la API.** Desde `http://localhost:8000/docs`,
endpoint `POST /predict`, con las últimas 145 horas.

Si el lote trae menos de 145 horas, la API va a responder con un error claro. Eso
**también es la respuesta correcta**: "necesita 145 horas de historia porque la
variable más exigente es el benceno de hace una semana".

**Paso 4 — Medirle el drift contra nuestra referencia.** Si el lote es grande,
se puede comparar con `drift.comparar_lote`.

**Lo que no hay que hacer:** ponerse a improvisar código nuevo delante del
profesor. Si algo no está previsto, decirlo: "eso no lo tenemos automatizado; lo
que sí tenemos es esto otro".

---

## Preguntas que probablemente hagan, y la respuesta corta

**¿Por qué 24 horas y no 1?**
Con una hora no se organiza nada. Y el horizonte de 24 es lo que obliga a ser
estrictas con el leakage.

**¿Por qué no usaron el MAPE?**
Porque engaña cuando el valor real es bajo. Nuestro lote 2 tiene el MAPE más alto
y no el peor MAE.

**¿Cómo garantizan que no hay leakage?**
No lo garantizamos con un comentario: está programado. `build_features.py` levanta
`ErrorDeLeakage` y detiene el proceso si alguien pide un rezago menor que el
horizonte. Y hay 19 pruebas que lo comprueban.

**¿Por qué gradient_boosting y no random_forest, si el MAE era parecido?**
Random forest se degradaba 68.4% de entrenamiento a validación. El criterio de
sobreajuste lo rechazó solo.

**¿Por qué alias y no stages en MLflow?**
Porque los stages quedaron obsoletos. Lo avisa la propia interfaz de MLflow.

**¿Por qué el reentrenamiento no es automático?**
Con un solo modelo y trece meses de historia, automatizarlo podría reemplazar un
modelo bueno por uno peor sin que nadie se entere. Con más datos y una comparación
previa contra el modelo vigente, sí lo automatizaríamos.

**¿De dónde salen los umbrales 0.10 y 0.25 del PSI?**
Del riesgo crediticio. No son leyes universales y lo decimos en el informe. Lo que
sí comprobamos es que el cálculo está bien: las variables de calendario dan PSI
cercano a cero, como tiene que ser.

**¿Y si el drift es alto pero el modelo anda bien?**
Es exactamente nuestro lote 3. Se decide VIGILAR, no reentrenar.

**¿Cuánto pesa la imagen y por qué?**
865 MB. Sacamos MLflow, matplotlib y statsmodels, que la API no necesita. Con todo
instalado eran 1.33 GB.

**¿Qué harían distinto?**
Conseguir más años de datos. Es lo que más movería la aguja.

---

## Si algo se rompe en vivo

**El contenedor dice `unhealthy`:**

```
docker logs demo --tail 30
```

Y mientras tanto, levantar la API sin Docker:

```
uvicorn src.api.main:app --port 8000
```

**MLflow no abre:** mostrar `models/produccion_info.json`, que trae el nombre del
modelo, la versión, el `run_id` y las métricas. Dice lo mismo.

**Un comando falla:** no repetirlo tres veces. Decir qué debería haber salido,
mostrar el resultado guardado en `reports/` o en `logs/pipeline.log`, y seguir.
Un error bien explicado cuesta menos que tres minutos de silencio.

**Se cae el internet:** todo el proyecto corre sin conexión, salvo la descarga
inicial de los datos, y esa ya está hecha.

---

## Para cerrar

Tres frases, no más:

1. "Construimos el camino completo, no solo un modelo: desde la descarga hasta un
   servicio vigilado."
2. "El hallazgo que más nos enseñó es que drift y degradación no son lo mismo, y
   lo medimos con nuestros propios datos."
3. "Y sabemos dónde están los límites: un solo lugar, un solo invierno, y un
   umbral que habría que ajustar con datos del negocio."

Y agradecer.

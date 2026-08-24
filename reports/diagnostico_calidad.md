# Diagnostico de calidad de datos

Generado por `python -m src.validation.diagnose`.

- Fuente: Air Quality (UCI, id 360)
- Filas: 9357
- Columnas: 13
- Periodo: 2004-03-10 18:00:00 a 2005-04-04 14:00:00
- Variable a pronosticar: `C6H6(GT)`

## 1. Valores faltantes

Los faltantes venian codificados como -200 y ya fueron convertidos a nulo
en la ingesta. La columna `bloque_mas_largo_h` es la clave: dice cuantas
horas seguidas estuvo sin medir.

| columna | nulos | pct | bloques | bloque_mas_largo_h |
|---|---|---|---|---|
| NMHC(GT) | 8443 | 90.23 | 6 | 8126 |
| CO(GT) | 1683 | 17.99 | 187 | 173 |
| NO2(GT) | 1642 | 17.55 | 344 | 173 |
| NOx(GT) | 1639 | 17.52 | 344 | 173 |
| PT08.S1(CO) | 366 | 3.91 | 16 | 76 |
| PT08.S2(NMHC) | 366 | 3.91 | 16 | 76 |
| C6H6(GT) | 366 | 3.91 | 16 | 76 |
| PT08.S3(NOx) | 366 | 3.91 | 16 | 76 |
| PT08.S4(NO2) | 366 | 3.91 | 16 | 76 |
| PT08.S5(O3) | 366 | 3.91 | 16 | 76 |
| T | 366 | 3.91 | 16 | 76 |
| RH | 366 | 3.91 | 16 | 76 |
| AH | 366 | 3.91 | 16 | 76 |

## 2. Duplicados

- Filas repetidas enteras: 0
- Timestamps repetidos: 0

## 3. Continuidad temporal

- Horas esperadas entre el primer y el ultimo registro: 9357
- Horas presentes: 9357
- Horas ausentes: 0

## 4. Apagones del arreglo de sensores

Hay dos instrumentos distintos en este dataset y fallan en momentos
distintos, asi que hay que mirarlos por separado:

- Arreglo de sensores (PT08.S1(CO), PT08.S2(NMHC), PT08.S3(NOx), PT08.S4(NO2), PT08.S5(O3), C6H6(GT), T, RH, AH)
- Analizador de referencia (CO(GT), NMHC(GT), NOx(GT), NO2(GT))

Filas donde el arreglo de sensores no midió absolutamente nada: 366
Filas donde al menos uno de ellos esta nulo: 366

Los dos números coinciden, lo que confirma que se apagan juntos: no son
fallas sueltas de un sensor, es el equipo completo fuera de servicio.

- Cantidad de bloques seguidos: 16
- Duración de cada bloque en horas: [76, 75, 52, 45, 38, 24, 14, 10, 9, 8, 5, 4, 3, 1, 1, 1]

## 5. Estadística descriptiva, sesgo y cardinalidad

| columna | min | p50 | max | media | desv | skew | unicos |
|---|---|---|---|---|---|---|---|
| CO(GT) | 0.1 | 1.8 | 11.9 | 2.15 | 1.45 | 1.37 | 96 |
| PT08.S1(CO) | 647.0 | 1063.0 | 2040.0 | 1099.83 | 217.08 | 0.756 | 1041 |
| NMHC(GT) | 7.0 | 150.0 | 1189.0 | 218.81 | 204.46 | 1.557 | 429 |
| C6H6(GT) | 0.1 | 8.2 | 63.7 | 10.08 | 7.45 | 1.362 | 407 |
| PT08.S2(NMHC) | 383.0 | 909.0 | 2214.0 | 939.15 | 266.83 | 0.562 | 1245 |
| NOx(GT) | 2.0 | 180.0 | 1479.0 | 246.9 | 212.98 | 1.716 | 925 |
| PT08.S3(NOx) | 322.0 | 806.0 | 2683.0 | 835.49 | 256.82 | 1.102 | 1221 |
| NO2(GT) | 2.0 | 109.0 | 340.0 | 113.09 | 48.37 | 0.622 | 283 |
| PT08.S4(NO2) | 551.0 | 1463.0 | 2775.0 | 1456.26 | 346.21 | 0.205 | 1603 |
| PT08.S5(O3) | 221.0 | 963.0 | 2523.0 | 1022.91 | 398.48 | 0.628 | 1743 |
| T | -1.9 | 17.8 | 44.6 | 18.32 | 8.83 | 0.309 | 436 |
| RH | 9.2 | 49.6 | 88.7 | 49.23 | 17.32 | -0.038 | 753 |
| AH | 0.18 | 1.0 | 2.23 | 1.03 | 0.4 | 0.251 | 6683 |

## 6. Datos imposibles

Rangos evaluados: {'T': (-20.0, 55.0), 'RH': (0.0, 100.0), 'AH': (0.0, 3.0), 'CO(GT)': (0.0, 100.0), 'C6H6(GT)': (0.0, 100.0), 'NOx(GT)': (0.0, 2000.0), 'NO2(GT)': (0.0, 1000.0)}

Resultado: ningún valor fuera de rango físico

## 7. Valores extremos

Criterio: fuera de Q1 - 3*RIC o Q3 + 3*RIC. Se cuentan, no se borran:
en contaminación del aire un pico alto suele ser un evento real.

| columna | extremos | pct |
|---|---|---|
| NOx(GT) | 75 | 0.97 |
| NMHC(GT) | 4 | 0.44 |
| CO(GT) | 27 | 0.35 |
| PT08.S3(NOx) | 29 | 0.32 |
| C6H6(GT) | 23 | 0.26 |
| NO2(GT) | 1 | 0.01 |
| PT08.S1(CO) | 0 | 0.0 |
| PT08.S2(NMHC) | 0 | 0.0 |
| PT08.S4(NO2) | 0 | 0.0 |
| PT08.S5(O3) | 0 | 0.0 |
| T | 0 | 0.0 |
| RH | 0 | 0.0 |
| AH | 0 | 0.0 |

## 8. Correlación con el target y riesgo de leakage

| columna | correlacion_con_target | filas_comparables |
|---|---|---|
| PT08.S2(NMHC) | 0.982 | 8991 |
| CO(GT) | 0.9311 | 7344 |
| NMHC(GT) | 0.9026 | 887 |
| PT08.S1(CO) | 0.8838 | 8991 |
| PT08.S5(O3) | 0.8657 | 8991 |
| PT08.S4(NO2) | 0.7657 | 8991 |
| PT08.S3(NOx) | -0.7357 | 8991 |
| NOx(GT) | 0.7188 | 7396 |
| NO2(GT) | 0.6145 | 7393 |
| T | 0.199 | 8991 |
| AH | 0.168 | 8991 |
| RH | -0.0617 | 8991 |

Columnas con correlación mayor a 0.95: ['PT08.S2(NMHC)']

Este numero no es una curiosidad estadística, es una advertencia. En este
dataset el valor de benceno se obtuvo calibrando la respuesta del sensor
PT08.S2(NMHC), asi que las dos columnas miden casi lo mismo.

Consecuencia para el modelado: como el problema es pronosticar el futuro,
solo se pueden usar valores de la hora t hacia atras para predecir la hora
t+24. Usar la lectura del mismo instante que queremos predecir daria un
resultado altisimo y falso.

## 9. Data Quality Gates

| codigo | regla | severidad | paso | detalle |
|---|---|---|---|---|
| R01 | esquema de columnas | dura | True | 13 columnas correctas |
| R02 | cantidad minima de filas | dura | True | 9357 filas (minimo 8000) |
| R03 | timestamps sin repetir | dura | True | 0 repetidos |
| R04 | continuidad horaria | blanda | True | 0 horas ausentes de 9357 esperadas |
| R05 | rangos fisicos posibles | dura | True | todos los valores dentro de rango |
| R06 | faltantes en el target | blanda | True | 3.91% de huecos (limite 10%) |
| R07 | filas duplicadas | dura | True | 0.000% duplicadas (limite 1%) |

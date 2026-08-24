"""
Metricas operativas del servicio.

Es el System Monitoring de la seccion N1: latencia, throughput, tasa de error y
disponibilidad. No hace falta instalar nada: cada peticion que pasa por la API
se anota aqui y ademas queda en logs/pipeline.log.

Se guardan en memoria las ultimas mil latencias. Con eso alcanza para sacar
mediana y percentil 95 sin que el consumo de memoria crezca sin control. Al
reiniciar el servicio el contador vuelve a cero, y esta bien: para un sistema
que tiene que sobrevivir reinicios haria falta una base de datos, y eso queda
fuera del alcance de este proyecto.
"""

import threading
import time
from collections import defaultdict, deque

import numpy as np

MAXIMO_LATENCIAS = 1000


class Contadores:
    def __init__(self):
        self._candado = threading.Lock()
        self.arranque = time.time()
        self.total = 0
        self.errores = 0
        self.latencias = deque(maxlen=MAXIMO_LATENCIAS)
        self.por_endpoint = defaultdict(lambda: {"peticiones": 0, "errores": 0,
                                                 "latencia_ms_total": 0.0})

    def anotar(self, endpoint, milisegundos, codigo):
        with self._candado:
            self.total += 1
            self.latencias.append(milisegundos)

            fila = self.por_endpoint[endpoint]
            fila["peticiones"] += 1
            fila["latencia_ms_total"] += milisegundos

            # 5xx es culpa del servicio. 4xx es culpa de quien llama, asi que no
            # cuenta como error nuestro para la disponibilidad.
            if codigo >= 500:
                self.errores += 1
                fila["errores"] += 1

    def resumen(self):
        with self._candado:
            en_pie = time.time() - self.arranque
            latencias = list(self.latencias)
            total = self.total
            errores = self.errores
            endpoints = {
                nombre: {
                    "peticiones": datos["peticiones"],
                    "errores": datos["errores"],
                    "latencia_ms_promedio": round(
                        datos["latencia_ms_total"] / datos["peticiones"], 2)
                    if datos["peticiones"] else 0.0,
                }
                for nombre, datos in self.por_endpoint.items()
            }

        tasa_error = errores / total if total else 0.0

        return {
            "segundos_en_pie": round(en_pie, 1),
            "peticiones_totales": total,
            "peticiones_con_error": errores,
            "tasa_de_error": round(tasa_error, 4),
            "disponibilidad": round(1 - tasa_error, 4),
            "throughput_por_minuto": round(total / en_pie * 60, 2) if en_pie > 0 else 0.0,
            "latencia_ms_p50": round(float(np.percentile(latencias, 50)), 2) if latencias else None,
            "latencia_ms_p95": round(float(np.percentile(latencias, 95)), 2) if latencias else None,
            "latencia_ms_maxima": round(float(max(latencias)), 2) if latencias else None,
            "por_endpoint": endpoints,
        }


contadores = Contadores()

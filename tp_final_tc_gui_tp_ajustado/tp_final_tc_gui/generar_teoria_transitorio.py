from pathlib import Path

import numpy as np

from func.analisis_datos import (
    generar_solucion_teorica,
    respuesta_rlc_subamortiguada,
)
from func.manejo_datos import guardar_csv_desde_arrays


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs" / "datos"


# ---------------------------------------------------------
# Configuración del eje temporal
# ---------------------------------------------------------

T_MIN = -20e-6       # segundos
T_MAX = 300e-6       # segundos
PUNTOS = 2000


# ---------------------------------------------------------
# Parámetros editables de la solución teórica
# ---------------------------------------------------------

VALOR_INICIAL = 0.0
VALOR_FINAL = 1.6
ALPHA = 12000.0
FRECUENCIA_NATURAL_HZ = 12000.0
DERIVADA_INICIAL = 0.0


def funcion_teorica(tiempo):
    """
    Escribí acá la función teórica del transitorio.

    tiempo está en segundos y puede tener valores negativos si querés
    mostrar un pequeño tramo antes del evento.

    La función debe devolver un vector del mismo tamaño que tiempo.
    """
    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    tiempo_positivo = np.maximum(
        tiempo,
        0
    )

    omega_0 = (
        2
        * np.pi
        * FRECUENCIA_NATURAL_HZ
    )

    respuesta = respuesta_rlc_subamortiguada(
        tiempo=tiempo_positivo,
        valor_inicial=VALOR_INICIAL,
        valor_final=VALOR_FINAL,
        alpha=ALPHA,
        omega_0=omega_0,
        derivada_inicial=DERIVADA_INICIAL,
    )

    return np.where(
        tiempo < 0,
        VALOR_INICIAL,
        respuesta
    )


def main():
    tiempo = np.linspace(
        T_MIN,
        T_MAX,
        PUNTOS
    )

    tiempo_teorico, channel_teorico = generar_solucion_teorica(
        tiempo,
        funcion_teorica
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    ruta_salida = (
        OUTPUT_DIR
        / "teoria_transitorio.csv"
    )

    guardar_csv_desde_arrays(
        ruta_salida,
        tiempo_teorico,
        channel_teorico,
        nombres=["teoria_v"]
    )

    print(
        f"Archivo generado: {ruta_salida}"
    )
    print(
        f"Formato: tiempo_s, teoria_v"
    )
    print(
        f"Puntos: {tiempo_teorico.size}"
    )


if __name__ == "__main__":
    main()

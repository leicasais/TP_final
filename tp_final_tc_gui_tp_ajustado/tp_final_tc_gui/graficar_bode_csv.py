from pathlib import Path

import numpy as np

from func.graficos import graficar_bode
from func.manejo_datos import guardar_datos, leer_datos


BASE_DIR = Path(__file__).resolve().parent
RUTA_CSV = BASE_DIR / "data" / "FILTRO_2.csv"
RUTA_SALIDA = BASE_DIR / "outputs" / "bode.png"


def main():
    df = leer_datos(
        RUTA_CSV
    )
    frecuencia, channel = guardar_datos(
        df
    )

    if channel.shape[0] < 2:
        raise ValueError(
            "El CSV debe tener tres columnas: frecuencia, módulo y fase."
        )

    modulo_db = channel[0]
    fase_grados = channel[1]

    if not np.any(frecuencia > 0):
        raise ValueError(
            "La primera columna no contiene frecuencias positivas. "
            "Para Bode debe ser frecuencia [Hz], no tiempo."
        )

    graficar_bode(
        frecuencia=frecuencia,
        modulo_db=modulo_db,
        fase_grados=fase_grados,
        ruta_salida=RUTA_SALIDA,
        mostrar=False,
    )

    print(
        f"Gráfico guardado en: {RUTA_SALIDA}"
    )


if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np


def leer_datos(archivo, skiprows=2, header=None, sep=","):
    """
    Lee un archivo tipo osciloscopio.

    Formato esperado:
        columna 0 -> tiempo
        columnas 1..n -> canales

    Por defecto ignora las dos primeras filas que exporta el
    osciloscopio:
        x-axis,1,2,...
        second,Volt,Volt,...
    """
    try:
        df = pd.read_csv(
            archivo,
            skiprows=skiprows,
            header=header,
            sep=sep
        )
        return df
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None


def leer_transitorio_ltspice(archivo):
    """
    Lee un .txt exportado desde LTspice.

    Formato típico:
        time    V(vout)
        0       ...
        ...
    """
    try:
        df = pd.read_csv(
            archivo,
            sep=r"\s+",
            engine="python"
        )
        return df
    except Exception as e:
        print(f"Error al leer el transitorio simulado: {e}")
        return None


def guardar_datos(df):
    """
    Convierte un DataFrame a los arrays usados por el graficador.

    Retorna:
        tiempo:
            vector unidimensional.

        channel:
            matriz donde cada fila es un canal y cada columna
            es una muestra.
    """
    if df is None:
        raise ValueError(
            "No se puede guardar datos porque el DataFrame es None."
        )

    if df.shape[1] < 2:
        raise ValueError(
            "El archivo debe tener una columna de tiempo "
            "y al menos una columna de datos."
        )

    datos = df.apply(
        pd.to_numeric,
        errors="coerce"
    )

    datos = datos.dropna(
        how="any"
    )

    if datos.empty:
        raise ValueError(
            "No quedaron filas numéricas válidas para graficar."
        )

    tiempo = datos.iloc[:, 0].to_numpy(
        dtype=float
    )

    channel = datos.iloc[:, 1:].to_numpy(
        dtype=float
    ).T

    return tiempo, channel


def guardar_csv_desde_arrays(ruta_salida, tiempo, channel, nombres=None):
    """
    Guarda arrays con el mismo criterio de formato:
        tiempo, curva_1, curva_2, ...

    Sirve para exportar los puntos de la solución teórica.
    """
    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    channel = np.asarray(
        channel,
        dtype=float
    )

    if channel.ndim == 1:
        channel = channel.reshape(1, -1)

    if tiempo.ndim != 1:
        raise ValueError(
            "El tiempo debe ser un vector."
        )

    if channel.ndim != 2:
        raise ValueError(
            "Channel debe ser una matriz."
        )

    if channel.shape[1] != tiempo.size:
        raise ValueError(
            "Las curvas no tienen la misma cantidad de puntos "
            "que el vector de tiempo."
        )

    if nombres is None:
        nombres = [
            f"curva_{i + 1}"
            for i in range(channel.shape[0])
        ]

    columnas = {
        "tiempo_s": tiempo
    }

    for nombre, curva in zip(nombres, channel):
        columnas[nombre] = curva

    df = pd.DataFrame(
        columnas
    )

    df.to_csv(
        ruta_salida,
        index=False
    )

    return df


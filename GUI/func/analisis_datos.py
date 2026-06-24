import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np
from pathlib import Path

def info_relevante_csv(tiempo):
    print("Tiempo mínimo:", tiempo.min())
    print("Tiempo máximo:", tiempo.max())
    print("Intervalo total:", tiempo.max() - tiempo.min())

def buscar_limites_transitorio(
    tiempo,
    channel,
    canal_referencia=0,
    escala_eje_x=1,
    escala_eje_y=1,
    tolerancia_final=5,
    muestras_estables=40,
    fraccion_datos_finales=0.10,
    contexto_anterior=0.10,
    contexto_posterior=0.10
):
    """
    Busca automáticamente una ventana apropiada
    para visualizar un transitorio.

    Retorna:
        x_min, x_max, y_min, y_max

    Los resultados se expresan en las unidades resultantes
    de escala_eje_x y escala_eje_y.

    tolerancia_final está expresada en porcentaje.
    """

    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    channel = np.asarray(
        channel,
        dtype=float
    )

    if tiempo.ndim != 1:
        raise ValueError(
            "El tiempo debe ser un vector unidimensional."
        )

    if channel.ndim != 2:
        raise ValueError(
            "Channel debe ser una matriz bidimensional."
        )

    if channel.shape[1] != tiempo.size:
        raise ValueError(
            "La cantidad de columnas de channel debe coincidir "
            "con la cantidad de muestras temporales."
        )

    if not 0 <= canal_referencia < channel.shape[0]:
        raise ValueError(
            "El canal de referencia no existe."
        )

    if tiempo.size < 3:
        raise ValueError(
            "No hay suficientes muestras para analizar."
        )

    tiempo_grafico = (
        tiempo * escala_eje_x
    )

    channel_grafico = (
        channel * escala_eje_y
    )

    referencia_original = (
        channel_grafico[canal_referencia]
    )

    # Rellenar posibles NaN solamente para detectar el evento.
    posiciones = np.arange(
        referencia_original.size
    )

    posiciones_validas = np.isfinite(
        referencia_original
    )

    if np.count_nonzero(posiciones_validas) < 3:
        raise ValueError(
            "El canal de referencia no contiene suficientes datos."
        )

    referencia = np.interp(
        posiciones,
        posiciones[posiciones_validas],
        referencia_original[posiciones_validas]
    )

    # -----------------------------------------------------
    # Inicio del transitorio: mayor cambio entre muestras
    # -----------------------------------------------------

    diferencias = np.abs(
        np.diff(referencia)
    )

    indice_inicio = (
        int(np.argmax(diferencias)) + 1
    )

    # -----------------------------------------------------
    # Valores inicial y final
    # -----------------------------------------------------

    valor_inicial = np.median(
        referencia[:indice_inicio]
    )

    cantidad_final = max(
        5,
        int(
            referencia.size
            * fraccion_datos_finales
        )
    )

    tramo_final = (
        referencia[-cantidad_final:]
    )

    valor_final = np.median(
        tramo_final
    )

    # -----------------------------------------------------
    # Estimación del ruido final
    # -----------------------------------------------------

    ruido_final = (
        1.4826
        * np.median(
            np.abs(
                tramo_final - valor_final
            )
        )
    )

    rango_referencia = (
        np.max(referencia)
        - np.min(referencia)
    )

    amplitud_cambio = abs(
        valor_final - valor_inicial
    )

    amplitud_referencia = max(
        amplitud_cambio,
        0.1 * rango_referencia,
        np.finfo(float).eps
    )

    tolerancia_absoluta = max(
        tolerancia_final
        / 100
        * amplitud_referencia,
        3 * ruido_final
    )

    # -----------------------------------------------------
    # Buscar cuándo queda estable
    # -----------------------------------------------------

    dentro_de_tolerancia = (
        np.abs(
            referencia - valor_final
        )
        <= tolerancia_absoluta
    )

    cantidad_posterior = (
        referencia.size - indice_inicio
    )

    ventana_estable = min(
        muestras_estables,
        cantidad_posterior
    )

    indice_fin = (
        referencia.size - 1
    )

    if ventana_estable >= 2:
        resultado_ventana = np.convolve(
            dentro_de_tolerancia[indice_inicio:]
            .astype(int),
            np.ones(
                ventana_estable,
                dtype=int
            ),
            mode="valid"
        )

        posiciones_estables = np.flatnonzero(
            resultado_ventana
            == ventana_estable
        )

        if posiciones_estables.size > 0:
            indice_fin = (
                indice_inicio
                + posiciones_estables[0]
                + ventana_estable
                - 1
            )

    # -----------------------------------------------------
    # Intervalo horizontal
    # -----------------------------------------------------

    duracion = (
        tiempo_grafico[indice_fin]
        - tiempo_grafico[indice_inicio]
    )

    if duracion <= 0:
        duracion = (
            tiempo_grafico[-1]
            - tiempo_grafico[0]
        ) * 0.1

    x_min = max(
        tiempo_grafico[0],
        tiempo_grafico[indice_inicio]
        - contexto_anterior * duracion
    )

    x_max = min(
        tiempo_grafico[-1],
        tiempo_grafico[indice_fin]
        + contexto_posterior * duracion
    )

    # -----------------------------------------------------
    # Límites verticales en esa ventana
    # -----------------------------------------------------

    mascara_intervalo = (
        (tiempo_grafico >= x_min)
        & (tiempo_grafico <= x_max)
    )

    channel_intervalo = (
        channel_grafico[:, mascara_intervalo]
    )

    y_min = np.nanmin(
        channel_intervalo
    )

    y_max = np.nanmax(
        channel_intervalo
    )

    return (
        x_min,
        x_max,
        y_min,
        y_max
    )
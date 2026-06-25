import numpy as np

def info_relevante_csv(tiempo):
    print("Tiempo mínimo:", tiempo.min())
    print("Tiempo máximo:", tiempo.max())
    print("Intervalo total:", tiempo.max() - tiempo.min())


def indice_inicio_transitorio(
    channel,
    canal_referencia=0,
    fraccion_inicial=0.03,
    muestras_iniciales_max=80,
    fraccion_rango_umbral=0.05,
    factor_ruido=8,
    numero_evento=1,
    tiempo=None,
    separacion_minima=1e-3,
):
    """
    Detecta el inicio del transitorio buscando el primer cambio
    significativo respecto del valor inicial.

    Antes se usaba el mayor salto entre muestras consecutivas. Eso falla
    en respuestas muy oscilatorias: el mayor salto puede aparecer dentro
    de la oscilación, no al comienzo del evento.
    """
    channel = np.asarray(
        channel,
        dtype=float
    )

    if channel.ndim == 1:
        referencia = channel
    elif channel.ndim == 2:
        if not 0 <= canal_referencia < channel.shape[0]:
            raise ValueError(
                "El canal de referencia no existe."
            )

        referencia = channel[canal_referencia]
    else:
        raise ValueError(
            "Channel debe ser vector o matriz."
        )

    indices_eventos = detectar_indices_transitorios(
        referencia,
        tiempo=tiempo,
        fraccion_inicial=fraccion_inicial,
        muestras_iniciales_max=muestras_iniciales_max,
        fraccion_rango_umbral=fraccion_rango_umbral,
        factor_ruido=factor_ruido,
        separacion_minima=separacion_minima,
    )

    if numero_evento < 1:
        raise ValueError(
            "numero_evento debe ser 1 o mayor."
        )

    if len(indices_eventos) >= numero_evento:
        return int(
            indices_eventos[numero_evento - 1]
        )

    if len(indices_eventos) > 0:
        raise ValueError(
            f"Se pidió el evento {numero_evento}, pero solo se "
            f"detectaron {len(indices_eventos)} evento(s)."
        )

    posiciones = np.arange(
        referencia.size
    )
    posiciones_validas = np.isfinite(
        referencia
    )
    referencia_limpia = np.interp(
        posiciones,
        posiciones[posiciones_validas],
        referencia[posiciones_validas]
    )

    return int(
        np.argmax(
            np.abs(
                np.diff(
                    referencia_limpia
                )
            )
        )
        + 1
    )


def detectar_indices_transitorios(
    referencia,
    tiempo=None,
    fraccion_inicial=0.03,
    muestras_iniciales_max=80,
    fraccion_rango_umbral=0.05,
    factor_ruido=8,
    separacion_minima=1e-3,
):
    """
    Devuelve los índices de los eventos detectados.

    Un evento se toma como el primer punto donde la señal se aparta
    significativamente del valor inicial. Luego se ignoran nuevos
    cruces durante separacion_minima segundos para no confundir las
    oscilaciones internas con eventos distintos.
    """
    referencia = np.asarray(
        referencia,
        dtype=float
    )

    if referencia.ndim != 1:
        raise ValueError(
            "La referencia debe ser un vector."
        )

    posiciones = np.arange(
        referencia.size
    )

    posiciones_validas = np.isfinite(
        referencia
    )

    if np.count_nonzero(posiciones_validas) < 3:
        raise ValueError(
            "No hay suficientes muestras válidas."
        )

    referencia_limpia = np.interp(
        posiciones,
        posiciones[posiciones_validas],
        referencia[posiciones_validas]
    )

    if tiempo is None:
        tiempo_limpio = posiciones.astype(float)
        separacion = max(
            1,
            int(separacion_minima)
        )
    else:
        tiempo_limpio = np.asarray(
            tiempo,
            dtype=float
        )

        if tiempo_limpio.shape != referencia_limpia.shape:
            raise ValueError(
                "tiempo y referencia deben tener la misma longitud."
            )

        separacion = separacion_minima

    cantidad_inicial = min(
        muestras_iniciales_max,
        max(
            5,
            int(
                referencia_limpia.size
                * fraccion_inicial
            )
        )
    )

    tramo_inicial = referencia_limpia[
        :cantidad_inicial
    ]

    valor_inicial = np.median(
        tramo_inicial
    )

    ruido_inicial = (
        1.4826
        * np.median(
            np.abs(
                tramo_inicial
                - valor_inicial
            )
        )
    )

    rango_total = (
        np.nanmax(
            referencia_limpia
        )
        - np.nanmin(
            referencia_limpia
        )
    )

    umbral = max(
        factor_ruido * ruido_inicial,
        fraccion_rango_umbral * rango_total,
        np.finfo(float).eps
    )

    posiciones_evento = np.flatnonzero(
        np.abs(
            referencia_limpia
            - valor_inicial
        )
        >= umbral
    )

    eventos = []
    proximo_tiempo_permitido = -np.inf

    for indice in posiciones_evento:
        tiempo_actual = tiempo_limpio[indice]

        if tiempo_actual >= proximo_tiempo_permitido:
            eventos.append(
                int(indice)
            )
            proximo_tiempo_permitido = (
                tiempo_actual
                + separacion
            )

    return eventos


def tiempo_relativo_transitorio(
    tiempo,
    channel,
    canal_referencia=0,
    numero_evento=1,
    separacion_minima=1e-3,
):
    """
    Desplaza el eje temporal para que t=0 coincida con el inicio
    estimado del transitorio.
    """
    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    indice_inicio = indice_inicio_transitorio(
        channel=channel,
        canal_referencia=canal_referencia,
        numero_evento=numero_evento,
        tiempo=tiempo,
        separacion_minima=separacion_minima,
    )

    return (
        tiempo - tiempo[indice_inicio],
        indice_inicio
    )


def recortar_intervalo(tiempo, channel, t_min=None, t_max=None):
    """
    Recorta tiempo y canales en un intervalo expresado en segundos.
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

    if channel.shape[1] != tiempo.size:
        raise ValueError(
            "Channel y tiempo no tienen longitudes compatibles."
        )

    mascara = np.isfinite(
        tiempo
    )

    if t_min is not None:
        mascara &= tiempo >= t_min

    if t_max is not None:
        mascara &= tiempo <= t_max

    return (
        tiempo[mascara],
        channel[:, mascara]
    )


def generar_solucion_teorica(tiempo, funcion_teorica):
    """
    Evalúa una función teórica y devuelve el formato usado por
    graficar_curva:
        tiempo -> vector
        channel -> matriz de una fila

    La función recibida debe aceptar tiempo en segundos:
        v = funcion_teorica(tiempo)
    """
    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    valores = np.asarray(
        funcion_teorica(tiempo),
        dtype=float
    )

    if valores.shape != tiempo.shape:
        raise ValueError(
            "La función teórica debe devolver un vector "
            "con la misma forma que tiempo."
        )

    return (
        tiempo,
        valores.reshape(1, -1)
    )


def respuesta_rlc_subamortiguada(
    tiempo,
    valor_inicial,
    valor_final,
    alpha,
    omega_0,
    derivada_inicial=0
):
    """
    Respuesta genérica de segundo orden subamortiguada.

    v(t) = vf + e^(-alpha t) [A cos(wd t) + B sin(wd t)]

    Editando los parámetros se puede modelar carga o descarga.
    """
    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    if alpha < 0:
        raise ValueError(
            "alpha debe ser positivo."
        )

    if omega_0 <= alpha:
        raise ValueError(
            "Para esta función se necesita omega_0 > alpha."
        )

    omega_d = np.sqrt(
        omega_0**2 - alpha**2
    )

    a = (
        valor_inicial - valor_final
    )

    b = (
        derivada_inicial
        + alpha * a
    ) / omega_d

    return (
        valor_final
        + np.exp(
            -alpha * tiempo
        )
        * (
            a * np.cos(
                omega_d * tiempo
            )
            + b * np.sin(
                omega_d * tiempo
            )
        )
    )


def respuesta_subamortiguada_con_pico(
    tiempo,
    valor_inicial,
    valor_final,
    alpha,
    frecuencia_pseudo_hz,
    valor_pico,
    tiempo_pico,
):
    """
    Respuesta subamortiguada parametrizada por el sobrepico.

    Usa:
        v(t) = vf + exp(-alpha t) [A cos(wd t) + B sin(wd t)]

    con:
        A = vi - vf

    y calcula B para que la curva pase por:
        v(tiempo_pico) = valor_pico

    Esto es útil para el TP cuando ya calculaste teóricamente el
    sobrepico y la pseudofrecuencia, y querés graficar esa curva
    junto con LTspice y el osciloscopio.
    """
    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    if alpha < 0:
        raise ValueError(
            "alpha debe ser positivo."
        )

    if frecuencia_pseudo_hz <= 0:
        raise ValueError(
            "La pseudofrecuencia debe ser positiva."
        )

    if tiempo_pico <= 0:
        raise ValueError(
            "El tiempo de pico debe ser positivo."
        )

    omega_d = (
        2
        * np.pi
        * frecuencia_pseudo_hz
    )

    a = (
        valor_inicial
        - valor_final
    )

    seno_pico = np.sin(
        omega_d
        * tiempo_pico
    )

    if abs(seno_pico) < 1e-12:
        raise ValueError(
            "Con esa pseudofrecuencia y ese tiempo de pico no se "
            "puede ajustar el sobrepico. Cambiá t pico o fpseudo."
        )

    b = (
        np.exp(
            alpha
            * tiempo_pico
        )
        * (
            valor_pico
            - valor_final
        )
        - a
        * np.cos(
            omega_d
            * tiempo_pico
        )
    ) / seno_pico

    tiempo_positivo = np.maximum(
        tiempo,
        0
    )

    respuesta = (
        valor_final
        + np.exp(
            -alpha
            * tiempo_positivo
        )
        * (
            a
            * np.cos(
                omega_d
                * tiempo_positivo
            )
            + b
            * np.sin(
                omega_d
                * tiempo_positivo
            )
        )
    )

    return np.where(
        tiempo < 0,
        valor_inicial,
        respuesta
    )

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

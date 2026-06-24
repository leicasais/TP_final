import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, MaxNLocator
import numpy as np
from pathlib import Path

# Si una separación de grilla fija generara más marcas que esto, se
# abandona MultipleLocator y se usa un locator automático. Evita el
# crash "Locator attempting to generate N ticks ... exceeds MAXTICKS"
# de matplotlib (su límite duro es 1000).
MAX_MARCAS = 1000


def aplicar_locator_seguro(eje, sep, limite_inferior, limite_superior,
                           max_marcas=MAX_MARCAS):
    """
    Aplica MultipleLocator(sep) al eje SÓLO si la cantidad de marcas
    resultante es razonable.

    Si (rango / sep) supera max_marcas —por ejemplo al cambiar la
    escala de unidades y dejar una separación muy chica— cae a un
    locator automático (MaxNLocator) en lugar de hacer crashear a
    matplotlib.
    """
    rango = abs(limite_superior - limite_inferior)

    if sep > 0 and np.isfinite(rango) and (rango / sep) <= max_marcas:
        eje.set_major_locator(MultipleLocator(sep))
    else:
        eje.set_major_locator(MaxNLocator(nbins="auto"))


def graficar_curva(
    tiempo,                    # Vector del eje x original
    channel,                   # Matriz: cada fila es un canal
    ruta_salida,               # Ruta y nombre del archivo de imagen

    x_min=None,                # Límite mínimo de x; None usa el mínimo de los datos
    x_max=None,                # Límite máximo de x; None usa el máximo de los datos
    y_min=None,                # Límite mínimo de y; None usa el mínimo de los canales
    y_max=None,                # Límite máximo de y; None usa el máximo de los canales

    escala_graf_x="linear",    # Tipo de eje x: "linear", "log" o "symlog"
    escala_graf_y="linear",    # Tipo de eje y: "linear", "log" o "symlog"

    escala_eje_x=1,            # Multiplica los valores de x para cambiar unidades. Por ejemplo si original en s -> us escala_eje_x=1e6
    escala_eje_y=1,            # Multiplica los valores de los canales

    sep_x=1,                   # Separación entre marcas principales del eje x
    sep_y=1,                   # Separación entre marcas principales del eje y

    margen_x=3,                # Margen horizontal agregado, en porcentaje
    margen_y=3,                # Margen vertical agregado, en porcentaje

    title="Señal medida",      # Título del gráfico
    unidad_x="Tiempo [s]",     # Texto y unidad del eje x
    unidad_y="Tensión [V]",    # Texto y unidad del eje y

    mostrar=True               # True muestra la ventana; False solo guarda
):
    
    """
    Grafica todos los canales en una misma imagen.

    Formato esperado:
        tiempo:
            vector unidimensional.

        channel:
            matriz donde:
            - cada fila es un canal;
            - cada columna es una muestra.

    Los límites x_min, x_max, y_min e y_max
    se expresan en las unidades mostradas en el gráfico,
    después de aplicar escala_eje_x y escala_eje_y.

    Si algún límite es None, se obtiene automáticamente
    de todos los datos.

    margen_x y margen_y están expresados en porcentaje.
    """

    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    channel = np.asarray(
        channel,
        dtype=float
    )

    # -----------------------------------------------------
    # Validación de los datos
    # -----------------------------------------------------

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
            "con la cantidad de valores de tiempo."
        )

    if tiempo.size == 0:
        raise ValueError(
            "No hay datos para graficar."
        )

    if escala_eje_x <= 0 or escala_eje_y <= 0:
        raise ValueError(
            "Los factores de escala deben ser positivos."
        )

    if sep_x <= 0 or sep_y <= 0:
        raise ValueError(
            "Las separaciones de los ejes deben ser positivas."
        )

    if escala_graf_x not in (
        "linear",
        "log",
        "symlog"
    ):
        raise ValueError(
            "escala_graf_x debe ser "
            "'linear', 'log' o 'symlog'."
        )

    if escala_graf_y not in (
        "linear",
        "log",
        "symlog"
    ):
        raise ValueError(
            "escala_graf_y debe ser "
            "'linear', 'log' o 'symlog'."
        )

    # -----------------------------------------------------
    # Cambio de unidades
    # -----------------------------------------------------

    tiempo_grafico = (
        tiempo * escala_eje_x
    )

    channel_grafico = (
        channel * escala_eje_y
    )

    if np.all(np.isnan(tiempo_grafico)):
        raise ValueError(
            "El eje x no contiene datos numéricos válidos."
        )

    if np.all(np.isnan(channel_grafico)):
        raise ValueError(
            "Los canales no contienen datos numéricos válidos."
        )

    # -----------------------------------------------------
    # Límites solicitados
    # -----------------------------------------------------

    if x_min is None:
        x_min = np.nanmin(
            tiempo_grafico
        )

    if x_max is None:
        x_max = np.nanmax(
            tiempo_grafico
        )

    if y_min is None:
        y_min = np.nanmin(
            channel_grafico
        )

    if y_max is None:
        y_max = np.nanmax(
            channel_grafico
        )

    if x_min >= x_max:
        raise ValueError(
            "x_min debe ser menor que x_max."
        )

    if y_min >= y_max:
        raise ValueError(
            "y_min debe ser menor que y_max."
        )

    # -----------------------------------------------------
    # Comprobaciones para escalas logarítmicas
    # -----------------------------------------------------

    if escala_graf_x == "log" and x_min <= 0:
        raise ValueError(
            "El límite inferior del eje x logarítmico "
            "debe ser mayor que cero."
        )

    if escala_graf_y == "log" and y_min <= 0:
        raise ValueError(
            "El límite inferior del eje y logarítmico "
            "debe ser mayor que cero."
        )

    # -----------------------------------------------------
    # Márgenes porcentuales
    # -----------------------------------------------------

    x_min_grafico, x_max_grafico = (
        agregar_margen_porcentual(
            limite_inferior=x_min,
            limite_superior=x_max,
            margen_porcentual=margen_x,
            escala=escala_graf_x
        )
    )

    y_min_grafico, y_max_grafico = (
        agregar_margen_porcentual(
            limite_inferior=y_min,
            limite_superior=y_max,
            margen_porcentual=margen_y,
            escala=escala_graf_y
        )
    )

    # -----------------------------------------------------
    # Crear figura y delegar el dibujo a aplicar_curva
    # -----------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(10, 6),
        layout="constrained"
    )

    aplicar_curva(
        fig=fig,
        ax=ax,
        tiempo_grafico=tiempo_grafico,
        channel_grafico=channel_grafico,
        x_min_grafico=x_min_grafico,
        x_max_grafico=x_max_grafico,
        y_min_grafico=y_min_grafico,
        y_max_grafico=y_max_grafico,
        escala_graf_x=escala_graf_x,
        escala_graf_y=escala_graf_y,
        sep_x=sep_x,
        sep_y=sep_y,
        title=title,
        unidad_x=unidad_x,
        unidad_y=unidad_y,
        mostrar_grilla=True,
    )

    # -----------------------------------------------------
    # Guardar imagen
    # -----------------------------------------------------

    ruta_salida = Path(
        ruta_salida
    )

    ruta_salida.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fig.savefig(
        ruta_salida,
        dpi=300,
        bbox_inches="tight"
    )

    if mostrar:
        plt.show()
    else:
        plt.close(fig)

    return fig, ax


def aplicar_curva(
    fig,
    ax,
    tiempo_grafico,
    channel_grafico,
    x_min_grafico,
    x_max_grafico,
    y_min_grafico,
    y_max_grafico,
    escala_graf_x="linear",
    escala_graf_y="linear",
    sep_x=1,
    sep_y=1,
    title="Señal medida",
    unidad_x="Tiempo [s]",
    unidad_y="Tensión [V]",
    mostrar_grilla=True,
    colores=None,
):
    """
    Dibuja los canales sobre una Figure y Axes ya existentes.

    Es la función que usa la GUI: recibe fig y ax creados por
    FigureCanvasTkAgg, los limpia y los rellena con los datos.
    graficar_curva() la llama internamente para no duplicar lógica.

    tiempo_grafico y channel_grafico ya tienen las unidades
    convertidas (escala_eje_x / escala_eje_y aplicadas) y los
    límites x/y ya incluyen el margen porcentual.

    colores: lista opcional de strings hex, uno por canal.
    """

    ax.cla()  # limpia el axes sin destruir la figura

    for i, canal in enumerate(channel_grafico):
        kwargs = dict(label=f"CH{i + 1}")
        if colores is not None and i < len(colores):
            kwargs["color"] = colores[i]
        ax.plot(tiempo_grafico, canal, **kwargs)

    ax.set_xscale(escala_graf_x)
    ax.set_yscale(escala_graf_y)

    if escala_graf_x == "linear":
        aplicar_locator_seguro(ax.xaxis, sep_x,
                               x_min_grafico, x_max_grafico)
    if escala_graf_y == "linear":
        aplicar_locator_seguro(ax.yaxis, sep_y,
                               y_min_grafico, y_max_grafico)

    ax.set_xlim(x_min_grafico, x_max_grafico)
    ax.set_ylim(y_min_grafico, y_max_grafico)

    ax.set_xlabel(unidad_x)
    ax.set_ylabel(unidad_y)
    ax.set_title(title)
    ax.legend()

    if mostrar_grilla:
        ax.grid(True, which="both", linestyle="--", alpha=0.5)
    else:
        ax.grid(False)

    return fig, ax

def agregar_margen_porcentual(
    limite_inferior,       # Límite mínimo antes de agregar margen
    limite_superior,       # Límite máximo antes de agregar margen
    margen_porcentual,     # Margen agregado en cada extremo, en porcentaje
    escala="linear"        # Tipo de eje: "linear" o "log"
):
    """
    Agrega un margen porcentual a un intervalo.

    Ejemplo lineal:
        límites: 0 y 100
        margen: 5 %
        resultado: -5 y 105

    Para escala logarítmica, el margen se calcula
    en el dominio logarítmico.
    """

    if margen_porcentual < 0:
        raise ValueError(
            "El margen porcentual no puede ser negativo."
        )

    if not np.isfinite(limite_inferior):
        raise ValueError(
            "El límite inferior no es válido."
        )

    if not np.isfinite(limite_superior):
        raise ValueError(
            "El límite superior no es válido."
        )

    if limite_inferior >= limite_superior:
        raise ValueError(
            "El límite inferior debe ser menor "
            "que el límite superior."
        )

    if margen_porcentual == 0:
        return limite_inferior, limite_superior

    if escala == "log":
        if limite_inferior <= 0:
            raise ValueError(
                "Los límites de una escala logarítmica "
                "deben ser positivos."
            )

        log_inferior = np.log10(limite_inferior)
        log_superior = np.log10(limite_superior)

        rango_logaritmico = (
            log_superior - log_inferior
        )

        margen_logaritmico = (
            rango_logaritmico
            * margen_porcentual
            / 100
        )

        limite_inferior_con_margen = 10 ** (
            log_inferior - margen_logaritmico
        )

        limite_superior_con_margen = 10 ** (
            log_superior + margen_logaritmico
        )

    else:
        rango = (
            limite_superior - limite_inferior
        )

        margen_absoluto = (
            rango
            * margen_porcentual
            / 100
        )

        limite_inferior_con_margen = (
            limite_inferior - margen_absoluto
        )

        limite_superior_con_margen = (
            limite_superior + margen_absoluto
        )

    return (
        limite_inferior_con_margen,
        limite_superior_con_margen
    )
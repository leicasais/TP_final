from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)

from func.analisis_datos import (
    generar_solucion_teorica,
    recortar_intervalo,
    respuesta_rlc_subamortiguada,
    respuesta_subamortiguada_con_pico,
    tiempo_relativo_transitorio,
)
from func.graficos import agregar_margen_porcentual, aplicar_curva
from func.manejo_datos import (
    guardar_csv_desde_arrays,
    guardar_datos,
    leer_datos,
    leer_transitorio_ltspice,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


def funcion_teorica_transitorio(tiempo, parametros):
    """
    Editá esta función si querés escribir otra solución teórica.

    Entrada:
        tiempo:
            vector en segundos. Si se alinea el transitorio, t=0
            es el inicio del salto.

        parametros:
            diccionario con valores leídos desde la GUI.

    Salida:
        vector de tensión con la misma forma que tiempo.

    La expresión usada por defecto es una respuesta de segundo orden
    subamortiguada:

        v(t) = vf + e^(-alpha t) [A cos(wd t) + B sin(wd t)]

    Para t < 0 se devuelve el valor inicial, así la teoría también
    muestra el tramo anterior al evento.
    """
    tiempo = np.asarray(
        tiempo,
        dtype=float
    )

    if parametros["usar_pico_teorico"]:
        return respuesta_subamortiguada_con_pico(
            tiempo=tiempo,
            valor_inicial=parametros["valor_inicial"],
            valor_final=parametros["valor_final"],
            alpha=parametros["alpha"],
            frecuencia_pseudo_hz=parametros["frecuencia_natural_hz"],
            valor_pico=parametros["valor_pico"],
            tiempo_pico=parametros["tiempo_pico"],
        )

    valor_inicial = parametros["valor_inicial"]
    valor_final = parametros["valor_final"]
    alpha = parametros["alpha"]
    omega_0 = 2 * np.pi * parametros["frecuencia_natural_hz"]
    derivada_inicial = parametros["derivada_inicial"]

    respuesta = respuesta_rlc_subamortiguada(
        tiempo=tiempo_positivo,
        valor_inicial=valor_inicial,
        valor_final=valor_final,
        alpha=alpha,
        omega_0=omega_0,
        derivada_inicial=derivada_inicial,
    )

    return np.where(
        tiempo < 0,
        valor_inicial,
        respuesta
    )


def interpolar_canal(tiempo_origen, channel_origen, tiempo_destino):
    """
    Interpola el primer canal de un archivo sobre el eje común.

    Fuera del rango medido devuelve NaN para que Matplotlib no invente
    datos que no existen.
    """
    tiempo_origen = np.asarray(
        tiempo_origen,
        dtype=float
    )

    channel_origen = np.asarray(
        channel_origen,
        dtype=float
    )

    if channel_origen.ndim == 2:
        canal = channel_origen[0]
    else:
        canal = channel_origen

    orden = np.argsort(
        tiempo_origen
    )

    tiempo_ordenado = tiempo_origen[orden]
    canal_ordenado = canal[orden]

    return np.interp(
        tiempo_destino,
        tiempo_ordenado,
        canal_ordenado,
        left=np.nan,
        right=np.nan
    )


class AplicacionTransitorio:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title(
            "Comparador de transitorios"
        )
        self.ventana.geometry(
            "1180x760"
        )

        self.ruta_csv_practica = tk.StringVar(
            value=str(DATA_DIR / "Carga.csv")
        )
        self.ruta_txt_simulacion = tk.StringVar(
            value=str(DATA_DIR / "Transitorio.txt")
        )

        self.tipo_grafico = tk.StringVar(
            value="Transitorio"
        )

        self.modo = tk.StringVar(
            value="Carga"
        )
        self.alinear_evento = tk.BooleanVar(
            value=True
        )
        self.evento_simulacion = tk.StringVar(
            value="1"
        )
        self.separacion_eventos_ms = tk.StringVar(
            value="1"
        )

        self.t_min_us = tk.StringVar(
            value="-20"
        )
        self.t_max_us = tk.StringVar(
            value="300"
        )
        self.cantidad_puntos = tk.StringVar(
            value="2000"
        )

        self.valor_inicial = tk.StringVar(
            value="0"
        )
        self.valor_final = tk.StringVar(
            value="0.655"
        )
        self.alpha = tk.StringVar(
            value="12000"
        )
        self.frecuencia_natural_hz = tk.StringVar(
            value="12000"
        )
        self.derivada_inicial = tk.StringVar(
            value="0"
        )
        self.usar_pico_teorico = tk.BooleanVar(
            value=True
        )
        self.valor_pico = tk.StringVar(
            value="5.21"
        )
        self.tiempo_pico_us = tk.StringVar(
            value="14"
        )
        self.escala_practica = tk.StringVar(
            value="1"
        )
        self.offset_practica = tk.StringVar(
            value="0"
        )
        self.escala_simulacion = tk.StringVar(
            value="1"
        )
        self.offset_simulacion = tk.StringVar(
            value="0"
        )
        self.escala_teoria = tk.StringVar(
            value="1"
        )
        self.offset_teoria = tk.StringVar(
            value="0"
        )
        self.texto_estadisticas = tk.StringVar(
            value="Sin datos graficados."
        )

        self.fig, self.ax = plt.subplots(
            figsize=(8.5, 5.5),
            layout="constrained"
        )

        self.crear_interfaz()

    def crear_interfaz(self):
        panel_principal = ttk.Frame(
            self.ventana,
            padding=10
        )
        panel_principal.pack(
            fill="both",
            expand=True
        )

        panel_controles = ttk.Frame(
            panel_principal
        )
        panel_controles.pack(
            side="left",
            fill="y",
            padx=(0, 12)
        )

        panel_grafico = ttk.Frame(
            panel_principal
        )
        panel_grafico.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.crear_controles_archivos(
            panel_controles
        )
        self.crear_controles_intervalo(
            panel_controles
        )
        self.crear_controles_teoria(
            panel_controles
        )
        self.crear_controles_escala(
            panel_controles
        )

        ttk.Button(
            panel_controles,
            text="Graficar comparación",
            command=self.graficar
        ).pack(
            fill="x",
            pady=(14, 4)
        )

        ttk.Button(
            panel_controles,
            text="Guardar teoría CSV",
            command=self.guardar_teoria
        ).pack(
            fill="x",
            pady=4
        )

        ttk.Label(
            panel_controles,
            textvariable=self.texto_estadisticas,
            justify="left",
            wraplength=330
        ).pack(
            fill="x",
            pady=(8, 0)
        )

        self.canvas = FigureCanvasTkAgg(
            self.fig,
            master=panel_grafico
        )
        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

        self.toolbar = NavigationToolbar2Tk(
            self.canvas,
            panel_grafico
        )
        self.toolbar.update()

    def crear_controles_archivos(self, padre):
        marco = ttk.LabelFrame(
            padre,
            text="Archivos"
        )
        marco.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            marco,
            text="CSV práctica"
        ).pack(
            anchor="w",
            padx=8,
            pady=(8, 0)
        )
        ttk.Entry(
            marco,
            textvariable=self.ruta_csv_practica,
            width=46
        ).pack(
            fill="x",
            padx=8
        )
        ttk.Button(
            marco,
            text="Elegir CSV",
            command=self.elegir_csv
        ).pack(
            fill="x",
            padx=8,
            pady=(4, 8)
        )

        ttk.Label(
            marco,
            text="TXT simulación LTspice"
        ).pack(
            anchor="w",
            padx=8
        )
        ttk.Entry(
            marco,
            textvariable=self.ruta_txt_simulacion,
            width=46
        ).pack(
            fill="x",
            padx=8
        )
        ttk.Button(
            marco,
            text="Elegir TXT",
            command=self.elegir_txt
        ).pack(
            fill="x",
            padx=8,
            pady=(4, 8)
        )

        ttk.Label(
            marco,
            text="Tipo de gráfico"
        ).pack(
            anchor="w",
            padx=8
        )
        ttk.Combobox(
            marco,
            textvariable=self.tipo_grafico,
            values=("Transitorio", "Bode"),
            state="readonly"
        ).pack(
            fill="x",
            padx=8,
            pady=(0, 8)
        )

        ttk.Label(
            marco,
            text="Modo"
        ).pack(
            anchor="w",
            padx=8
        )
        combo = ttk.Combobox(
            marco,
            textvariable=self.modo,
            values=("Carga", "Descarga"),
            state="readonly"
        )
        combo.pack(
            fill="x",
            padx=8,
            pady=(0, 8)
        )
        combo.bind(
            "<<ComboboxSelected>>",
            self.actualizar_valores_modo
        )

        ttk.Checkbutton(
            marco,
            text="Alinear por inicio del transitorio",
            variable=self.alinear_evento
        ).pack(
            anchor="w",
            padx=8,
            pady=(0, 8)
        )

        self.crear_fila_entrada(
            marco,
            "Evento simulación",
            self.evento_simulacion
        )
        self.crear_fila_entrada(
            marco,
            "Separación eventos [ms]",
            self.separacion_eventos_ms
        )

    def crear_controles_intervalo(self, padre):
        marco = ttk.LabelFrame(
            padre,
            text="Intervalo"
        )
        marco.pack(
            fill="x",
            pady=(0, 10)
        )

        self.crear_fila_entrada(
            marco,
            "t mínimo [us]",
            self.t_min_us
        )
        self.crear_fila_entrada(
            marco,
            "t máximo [us]",
            self.t_max_us
        )
        self.crear_fila_entrada(
            marco,
            "Puntos eje común",
            self.cantidad_puntos
        )

    def crear_controles_teoria(self, padre):
        marco = ttk.LabelFrame(
            padre,
            text="Solución teórica"
        )
        marco.pack(
            fill="x"
        )

        self.crear_fila_entrada(
            marco,
            "Valor inicial [V]",
            self.valor_inicial
        )
        self.crear_fila_entrada(
            marco,
            "Valor final [V]",
            self.valor_final
        )
        self.crear_fila_entrada(
            marco,
            "alpha [1/s]",
            self.alpha
        )
        self.crear_fila_entrada(
            marco,
            "fpseudo [Hz]",
            self.frecuencia_natural_hz
        )
        self.crear_fila_entrada(
            marco,
            "dv/dt inicial [V/s]",
            self.derivada_inicial
        )
        ttk.Checkbutton(
            marco,
            text="Forzar sobrepico teórico",
            variable=self.usar_pico_teorico
        ).pack(
            anchor="w",
            padx=8,
            pady=(4, 0)
        )
        self.crear_fila_entrada(
            marco,
            "Pico teórico [V]",
            self.valor_pico
        )
        self.crear_fila_entrada(
            marco,
            "t pico [us]",
            self.tiempo_pico_us
        )

    def crear_controles_escala(self, padre):
        marco = ttk.LabelFrame(
            padre,
            text="Escala y offset"
        )
        marco.pack(
            fill="x",
            pady=(10, 0)
        )

        self.crear_fila_entrada(
            marco,
            "Escala práctica",
            self.escala_practica
        )
        self.crear_fila_entrada(
            marco,
            "Offset práctica [V]",
            self.offset_practica
        )
        self.crear_fila_entrada(
            marco,
            "Escala simulación",
            self.escala_simulacion
        )
        self.crear_fila_entrada(
            marco,
            "Offset simulación [V]",
            self.offset_simulacion
        )
        self.crear_fila_entrada(
            marco,
            "Escala teoría",
            self.escala_teoria
        )
        self.crear_fila_entrada(
            marco,
            "Offset teoría [V]",
            self.offset_teoria
        )

    def crear_fila_entrada(self, padre, texto, variable):
        fila = ttk.Frame(
            padre
        )
        fila.pack(
            fill="x",
            padx=8,
            pady=4
        )

        ttk.Label(
            fila,
            text=texto,
            width=19
        ).pack(
            side="left"
        )

        ttk.Entry(
            fila,
            textvariable=variable,
            width=14
        ).pack(
            side="right",
            fill="x",
            expand=True
        )

    def elegir_csv(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar CSV de práctica",
            filetypes=[
                ("Archivos CSV", "*.csv"),
                ("Todos los archivos", "*.*"),
            ]
        )

        if ruta:
            self.ruta_csv_practica.set(
                ruta
            )

    def elegir_txt(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar TXT de LTspice",
            filetypes=[
                ("Archivos TXT", "*.txt"),
                ("Todos los archivos", "*.*"),
            ]
        )

        if ruta:
            self.ruta_txt_simulacion.set(
                ruta
            )

    def actualizar_valores_modo(self, _evento=None):
        if self.modo.get() == "Carga":
            self.valor_inicial.set(
                "0"
            )
            self.valor_final.set(
                "0.655"
            )
            self.evento_simulacion.set(
                "1"
            )
            self.valor_pico.set(
                "5.21"
            )
            self.tiempo_pico_us.set(
                "14"
            )
        else:
            self.valor_inicial.set(
                "0.655"
            )
            self.valor_final.set(
                "0"
            )
            self.evento_simulacion.set(
                "2"
            )
            self.valor_pico.set(
                "-8.5"
            )
            self.tiempo_pico_us.set(
                "13"
            )

    def leer_parametros(self):
        try:
            t_min = float(
                self.t_min_us.get()
            ) * 1e-6
            t_max = float(
                self.t_max_us.get()
            ) * 1e-6
            puntos = int(
                self.cantidad_puntos.get()
            )

            parametros = {
                "valor_inicial": float(self.valor_inicial.get()),
                "valor_final": float(self.valor_final.get()),
                "alpha": float(self.alpha.get()),
                "frecuencia_natural_hz": float(
                    self.frecuencia_natural_hz.get()
                ),
                "derivada_inicial": float(
                    self.derivada_inicial.get()
                ),
                "usar_pico_teorico": self.usar_pico_teorico.get(),
                "valor_pico": float(
                    self.valor_pico.get()
                ),
                "tiempo_pico": float(
                    self.tiempo_pico_us.get()
                )
                * 1e-6,
            }
        except ValueError as error:
            raise ValueError(
                "Hay un parámetro numérico mal escrito."
            ) from error

        if t_min >= t_max:
            raise ValueError(
                "t mínimo debe ser menor que t máximo."
            )

        if puntos < 10:
            raise ValueError(
                "Usá al menos 10 puntos para el eje común."
            )

        return t_min, t_max, puntos, parametros

    def leer_transformaciones(self):
        try:
            return {
                "practica": (
                    float(self.escala_practica.get()),
                    float(self.offset_practica.get()),
                ),
                "simulacion": (
                    float(self.escala_simulacion.get()),
                    float(self.offset_simulacion.get()),
                ),
                "teoria": (
                    float(self.escala_teoria.get()),
                    float(self.offset_teoria.get()),
                ),
            }
        except ValueError as error:
            raise ValueError(
                "Hay una escala u offset mal escrito."
            ) from error

    def aplicar_transformacion(self, channel, escala, offset):
        return (
            np.asarray(
                channel,
                dtype=float
            )
            * escala
            + offset
        )

    def ajustar_sobrepico_teorico(self, channel_teoria, parametros):
        """
        Si se fuerza el sobrepico, escala la parte variable de la
        teoría para que el máximo o mínimo visible coincida con el
        valor calculado.
        """
        if not parametros["usar_pico_teorico"]:
            return channel_teoria

        valores = np.asarray(
            channel_teoria,
            dtype=float
        ).copy()

        referencia = parametros["valor_final"]
        objetivo = parametros["valor_pico"]

        if objetivo >= referencia:
            actual = np.nanmax(
                valores[0]
            )
        else:
            actual = np.nanmin(
                valores[0]
            )

        denominador = (
            actual
            - referencia
        )

        if abs(denominador) < 1e-12:
            return valores

        factor = (
            objetivo
            - referencia
        ) / denominador

        valores[0] = (
            referencia
            + factor
            * (
                valores[0]
                - referencia
            )
        )

        return valores

    def cargar_curva_csv(self):
        df = leer_datos(
            self.ruta_csv_practica.get()
        )
        tiempo, channel = guardar_datos(
            df
        )

        if self.alinear_evento.get():
            tiempo, _ = tiempo_relativo_transitorio(
                tiempo,
                channel
            )

        return tiempo, channel

    def cargar_curva_txt(self):
        ruta = self.ruta_txt_simulacion.get()

        if not ruta:
            return None, None

        df = leer_transitorio_ltspice(
            ruta
        )
        tiempo, channel = guardar_datos(
            df
        )

        if self.alinear_evento.get():
            try:
                numero_evento = int(
                    self.evento_simulacion.get()
                )
                separacion_minima = (
                    float(
                        self.separacion_eventos_ms.get()
                    )
                    * 1e-3
                )
            except ValueError as error:
                raise ValueError(
                    "Evento simulación y separación de eventos "
                    "deben ser valores numéricos."
                ) from error

            tiempo, _ = tiempo_relativo_transitorio(
                tiempo,
                channel,
                numero_evento=numero_evento,
                separacion_minima=separacion_minima,
            )

        return tiempo, channel

    def preparar_datos_bode(self):
        """
        Lee un CSV de Bode con formato:
            columna 0 -> frecuencia [Hz]
            columna 1 -> módulo [dB]
            columna 2 -> fase [grados]
        """
        df = leer_datos(
            self.ruta_csv_practica.get()
        )
        frecuencia, channel = guardar_datos(
            df
        )

        if channel.shape[0] < 2:
            raise ValueError(
                "Para graficar Bode el CSV debe tener tres columnas: "
                "frecuencia, módulo y fase."
            )

        modulo_db = channel[0]
        fase_grados = channel[1]

        mascara = (
            np.isfinite(frecuencia)
            & np.isfinite(modulo_db)
            & np.isfinite(fase_grados)
            & (frecuencia > 0)
        )

        frecuencia = frecuencia[mascara]
        modulo_db = modulo_db[mascara]
        fase_grados = fase_grados[mascara]

        if frecuencia.size == 0:
            raise ValueError(
                "No quedaron frecuencias positivas. "
                "Para un Bode, la primera columna debe ser frecuencia "
                "en Hz y mayor que cero."
            )

        orden = np.argsort(
            frecuencia
        )

        return (
            frecuencia[orden],
            modulo_db[orden],
            fase_grados[orden]
        )

    def preparar_datos(self):
        t_min, t_max, puntos, parametros = self.leer_parametros()
        transformaciones = self.leer_transformaciones()

        tiempo_comun = np.linspace(
            t_min,
            t_max,
            puntos
        )

        series = []

        tiempo_practica, channel_practica = self.cargar_curva_csv()
        tiempo_practica, channel_practica = recortar_intervalo(
            tiempo_practica,
            channel_practica,
            t_min=t_min,
            t_max=t_max
        )
        escala, offset = transformaciones["practica"]
        channel_practica = self.aplicar_transformacion(
            channel_practica,
            escala,
            offset
        )
        series.append(
            {
                "tiempo": tiempo_practica,
                "valores": channel_practica[0],
                "etiqueta": f"Práctica {self.modo.get().lower()}",
                "estilo": "-",
            }
        )

        tiempo_txt, channel_txt = self.cargar_curva_txt()
        if tiempo_txt is not None:
            tiempo_txt, channel_txt = recortar_intervalo(
                tiempo_txt,
                channel_txt,
                t_min=t_min,
                t_max=t_max
            )

            if tiempo_txt.size > 1:
                escala, offset = transformaciones["simulacion"]
                channel_txt = self.aplicar_transformacion(
                    channel_txt,
                    escala,
                    offset
                )
                series.append(
                    {
                        "tiempo": tiempo_txt,
                        "valores": channel_txt[0],
                        "etiqueta": "Simulación LTspice",
                        "estilo": "--",
                    }
                )

        def teoria(t):
            return funcion_teorica_transitorio(
                t,
                parametros
            )

        _, channel_teoria = generar_solucion_teorica(
            tiempo_comun,
            teoria
        )
        channel_teoria = self.ajustar_sobrepico_teorico(
            channel_teoria,
            parametros
        )
        escala, offset = transformaciones["teoria"]
        channel_teoria = self.aplicar_transformacion(
            channel_teoria,
            escala,
            offset
        )
        series.append(
            {
                "tiempo": tiempo_comun,
                "valores": channel_teoria[0],
                "etiqueta": "Solución teórica",
                "estilo": ":",
            }
        )

        return (
            series,
            channel_teoria
        )

    def graficar(self):
        if self.tipo_grafico.get() == "Bode":
            self.graficar_bode_gui()
            return

        self.graficar_transitorio_gui()

    def asegurar_un_eje(self):
        if len(self.fig.axes) != 1:
            self.fig.clear()
            self.ax = self.fig.subplots(
                1,
                1
            )
        else:
            self.ax = self.fig.axes[0]

    def graficar_transitorio_gui(self):
        try:
            self.asegurar_un_eje()

            (
                series,
                _channel_teoria,
            ) = self.preparar_datos()

            self.ax.cla()

            todos_los_tiempos = []
            todos_los_valores = []
            resumen = []

            for serie in series:
                tiempo_us = (
                    serie["tiempo"]
                    * 1e6
                )
                valores = serie["valores"]

                self.ax.plot(
                    tiempo_us,
                    valores,
                    linestyle=serie["estilo"],
                    label=serie["etiqueta"]
                )

                todos_los_tiempos.append(
                    tiempo_us
                )
                todos_los_valores.append(
                    valores
                )

                indice_maximo = int(
                    np.nanargmax(
                        valores
                    )
                )
                indice_minimo = int(
                    np.nanargmin(
                        valores
                    )
                )
                tramo_final = valores[
                    max(
                        0,
                        int(0.8 * valores.size)
                    ):
                ]
                resumen.append(
                    f"{serie['etiqueta']}: "
                    f"max={valores[indice_maximo]:.3g} V "
                    f"en {tiempo_us[indice_maximo]:.3g} us, "
                    f"min={valores[indice_minimo]:.3g} V, "
                    f"final~{np.nanmedian(tramo_final):.3g} V"
                )

            tiempo_total = np.concatenate(
                todos_los_tiempos
            )
            valores_totales = np.concatenate(
                todos_los_valores
            )

            x_min = np.nanmin(
                tiempo_total
            )
            x_max = np.nanmax(
                tiempo_total
            )
            y_min = np.nanmin(
                valores_totales
            )
            y_max = np.nanmax(
                valores_totales
            )

            if y_min == y_max:
                y_min -= 1
                y_max += 1

            x_min_grafico, x_max_grafico = agregar_margen_porcentual(
                x_min,
                x_max,
                3,
                escala="linear"
            )
            y_min_grafico, y_max_grafico = agregar_margen_porcentual(
                y_min,
                y_max,
                5,
                escala="linear"
            )

            self.ax.set_xlim(
                x_min_grafico,
                x_max_grafico
            )
            self.ax.set_ylim(
                y_min_grafico,
                y_max_grafico
            )
            self.ax.set_xlabel(
                "Tiempo relativo [us]"
            )
            self.ax.set_ylabel(
                "Tensión [V]"
            )
            self.ax.set_title(
                f"Comparación transitorio de {self.modo.get().lower()}"
            )
            self.ax.grid(
                True,
                which="both",
                linestyle="--",
                alpha=0.5
            )
            self.ax.legend()

            self.texto_estadisticas.set(
                "\n".join(
                    resumen
                )
            )

            self.canvas.draw()

            OUTPUT_DIR.mkdir(
                parents=True,
                exist_ok=True
            )
            self.fig.savefig(
                OUTPUT_DIR / f"comparacion_{self.modo.get().lower()}.png",
                dpi=300,
                bbox_inches="tight"
            )

        except Exception as error:
            messagebox.showerror(
                "No se pudo graficar",
                str(error)
            )

    def graficar_bode_gui(self):
        try:
            frecuencia, modulo_db, fase_grados = self.preparar_datos_bode()

            self.fig.clear()
            ax_modulo, ax_fase = self.fig.subplots(
                2,
                1,
                sharex=True
            )
            self.ax = ax_modulo

            ax_modulo.semilogx(
                frecuencia,
                modulo_db,
                label="Módulo"
            )
            ax_modulo.set_ylabel(
                "Módulo [dB]"
            )
            ax_modulo.set_title(
                "Respuesta en frecuencia"
            )
            ax_modulo.grid(
                True,
                which="both",
                linestyle="--",
                alpha=0.5
            )
            ax_modulo.legend()

            ax_fase.semilogx(
                frecuencia,
                fase_grados,
                color="tab:orange",
                label="Fase"
            )
            ax_fase.set_xlabel(
                "Frecuencia [Hz]"
            )
            ax_fase.set_ylabel(
                "Fase [°]"
            )
            ax_fase.grid(
                True,
                which="both",
                linestyle="--",
                alpha=0.5
            )
            ax_fase.legend()

            self.fig.tight_layout()
            self.canvas.draw()

            OUTPUT_DIR.mkdir(
                parents=True,
                exist_ok=True
            )
            self.fig.savefig(
                OUTPUT_DIR / "bode.png",
                dpi=300,
                bbox_inches="tight"
            )

        except Exception as error:
            messagebox.showerror(
                "No se pudo graficar Bode",
                str(error)
            )

    def guardar_teoria(self):
        try:
            (
                series,
                channel_teoria,
            ) = self.preparar_datos()

            tiempo_teoria = series[-1]["tiempo"]

            ruta_salida = (
                OUTPUT_DIR
                / "datos"
                / f"teoria_{self.modo.get().lower()}.csv"
            )
            ruta_salida.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            guardar_csv_desde_arrays(
                ruta_salida,
                tiempo_teoria,
                channel_teoria,
                nombres=["teoria_v"]
            )

            messagebox.showinfo(
                "Teoría guardada",
                f"Archivo creado:\n{ruta_salida}"
            )

        except Exception as error:
            messagebox.showerror(
                "No se pudo guardar",
                str(error)
            )


def main():
    ventana = tk.Tk()
    AplicacionTransitorio(
        ventana
    )
    ventana.mainloop()


if __name__ == "__main__":
    main()

"""
GUI para visualización de datos de osciloscopio — TC1
"""
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from pathlib import Path
import re
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from func.manejo_datos   import leer_datos, guardar_datos
from func.analisis_datos import buscar_limites_transitorio
from func.graficos       import aplicar_curva, agregar_margen_porcentual

# ── Paleta ────────────────────────────────────────────────────────────────────
BG    = "#1e1e2e"
BG2   = "#13131f"
FG    = "#cdd6f4"
ACENT = "#89b4fa"
ENTRY = "#313244"
BORDE = "#45475a"
VERDE = "#a6e3a1"
GRIS  = "#6c7086"
ROJO  = "#f38ba8"

# Colores iniciales de los canales (editables en tiempo real)
COLORES_DEFAULT = ["#2196F3", "#F44336", "#4CAF50", "#FF9800"]


# ─────────────────────────────────────────────────────────────────────────────
class SeccionColapsable(tk.Frame):
    """
    Sección plegable: un encabezado clickeable que muestra u oculta su
    contenido. Reemplaza al LabelFrame para que el panel ocupe poco alto:
    se abre sólo la sección que se quiere editar y casi nunca hace falta
    scrollear.

    Uso:
        sec = SeccionColapsable(parent, "Título", abierto=False)
        sec.pack(fill=tk.X)
        # los controles se crean DENTRO de sec.body:
        tk.Label(sec.body, text="...").grid(...)

    on_toggle: callback opcional que se llama al abrir/cerrar (lo usamos
    para refrescar el área scrolleable del canvas).
    """

    def __init__(self, parent, titulo, abierto=False, on_toggle=None):
        super().__init__(parent, bg=BG, bd=1, relief="groove")
        self._titulo    = titulo
        self._on_toggle = on_toggle
        self.abierto    = abierto

        # Encabezado clickeable (la flecha indica el estado)
        self.header = tk.Label(
            self, bg=BG, fg=ACENT, font=("Consolas", 9, "bold"),
            anchor="w", padx=6, pady=5, cursor="hand2",
            text=self._texto_header()
        )
        self.header.pack(fill=tk.X)
        self.header.bind("<Button-1>", lambda _: self.toggle())

        # Cuerpo: acá van los controles de cada sección
        self.body = tk.Frame(self, bg=BG, padx=6, pady=4)
        if self.abierto:
            self.body.pack(fill=tk.X)

    def _texto_header(self):
        flecha = "▼" if self.abierto else "▶"
        return f"{flecha}  {self._titulo}"

    def toggle(self):
        self.abierto = not self.abierto
        if self.abierto:
            self.body.pack(fill=tk.X)
        else:
            self.body.pack_forget()
        self.header.config(text=self._texto_header())
        if self._on_toggle:
            self._on_toggle()


# ─────────────────────────────────────────────────────────────────────────────
class OscilloscopeGUI:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Visualizador de Osciloscopio — TC1")
        self.root.minsize(1000, 680)

        self.tiempo  = None
        self.channel = None

        # Color de fondo del gráfico (modificable por el usuario)
        self.color_fondo_fig = BG
        self.color_fondo_ax  = BG2

        # Timer para debounce (evitar re-graficar en cada tecla)
        self._timer_id = None

        self._construir_menu()
        self._construir_layout()

    # =========================================================================
    # MENÚ
    # =========================================================================
    def _construir_menu(self):
        barra = tk.Menu(self.root)
        m = tk.Menu(barra, tearoff=0)
        m.add_command(label="Abrir CSV…",      command=self._abrir,   accelerator="Ctrl+O")
        m.add_command(label="Guardar imagen…", command=self._guardar, accelerator="Ctrl+S")
        m.add_separator()
        m.add_command(label="Salir", command=self.root.quit)
        barra.add_cascade(label="Archivo", menu=m)
        self.root.config(menu=barra)
        self.root.bind("<Control-o>", lambda _: self._abrir())
        self.root.bind("<Control-s>", lambda _: self._guardar())

    # =========================================================================
    # LAYOUT PRINCIPAL
    # =========================================================================
    def _construir_layout(self):
        # ── Panel izquierdo: scrolleable ─────────────────────────────────────
        # Contenedor externo de ancho fijo
        outer = tk.Frame(self.root, width=275, bg=BG)
        outer.pack(side=tk.LEFT, fill=tk.Y)
        outer.pack_propagate(False)

        # Canvas de tkinter (no matplotlib) que actúa como viewport
        self._scroll_canvas = tk.Canvas(outer, bg=BG, highlightthickness=0,
                                         width=275)
        self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar vertical conectada al canvas
        sb = tk.Scrollbar(outer, orient=tk.VERTICAL,
                          command=self._scroll_canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._scroll_canvas.configure(yscrollcommand=sb.set)

        # Frame real donde viven todos los controles
        self.panel_ctrl = tk.Frame(self._scroll_canvas, bg=BG, padx=8, pady=8)
        # create_window incrusta el Frame dentro del Canvas
        self._win_id = self._scroll_canvas.create_window(
            (0, 0), window=self.panel_ctrl, anchor="nw"
        )

        # Cada vez que el Frame cambia de tamaño, actualizar scrollregion
        self.panel_ctrl.bind("<Configure>", self._on_frame_configure)
        # Cuando el canvas cambia de ancho, ajustar el frame al mismo ancho
        self._scroll_canvas.bind("<Configure>", self._on_canvas_configure)

        # Scroll con la rueda del mouse.
        # Se ata a TODA la app (bind_all) porque, si solo se atara al
        # canvas, la rueda no funcionaría cuando el puntero está encima
        # de un control hijo (Label, Entry, botón). En el handler se
        # filtra para scrollear únicamente cuando el puntero está sobre
        # el panel de controles.
        self.root.bind_all("<MouseWheel>", self._on_wheel)   # Windows / macOS
        self.root.bind_all("<Button-4>",   self._on_wheel)   # Linux (arriba)
        self.root.bind_all("<Button-5>",   self._on_wheel)   # Linux (abajo)

        # ── Panel derecho: gráfico ────────────────────────────────────────────
        self.panel_graf = tk.Frame(self.root, bg=BG2)
        self.panel_graf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._construir_controles()
        self._construir_grafico()

    def _on_frame_configure(self, _=None):
        """Actualiza el área scrolleable cuando el Frame interno cambia de tamaño."""
        self._scroll_canvas.configure(
            scrollregion=self._scroll_canvas.bbox("all")
        )

    def _on_canvas_configure(self, event):
        """Hace que el Frame interno tenga el mismo ancho que el Canvas."""
        self._scroll_canvas.itemconfig(self._win_id, width=event.width)

    def _sobre_panel(self, widget) -> bool:
        """True si `widget` es el canvas de controles o un descendiente suyo."""
        while widget is not None:
            if widget is self._scroll_canvas or widget is self.panel_ctrl:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _on_wheel(self, event):
        """
        Scrollea el panel de controles con la rueda, pero sólo cuando el
        puntero está sobre él (así la rueda sobre el gráfico no lo mueve).
        winfo_containing devuelve el widget que está debajo del puntero.
        """
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if not self._sobre_panel(widget):
            return

        if getattr(event, "num", None) == 4:        # Linux: rueda arriba
            paso = -1
        elif getattr(event, "num", None) == 5:      # Linux: rueda abajo
            paso = 1
        else:                                        # Windows / macOS
            paso = int(-1 * (event.delta / 120))

        self._scroll_canvas.yview_scroll(paso, "units")

    # =========================================================================
    # CONTROLES
    # =========================================================================
    def _construir_controles(self):
        p = self.panel_ctrl
        self._secciones = []   # para "expandir/colapsar todo"

        # ── Helpers de estilo ─────────────────────────────────────────────────
        def lbl(parent, texto):
            return tk.Label(parent, text=texto, bg=BG, fg=FG,
                            font=("Consolas", 9))

        def entry_num(parent, valor="", width=9):
            e = tk.Entry(parent, width=width, bg=ENTRY, fg=FG,
                         insertbackground=FG, relief="flat",
                         font=("Consolas", 9))
            if valor != "":
                e.insert(0, str(valor))
            # Actualizar al salir del campo o presionar Enter
            e.bind("<FocusOut>", lambda _: self._graficar_auto())
            e.bind("<Return>",   lambda _: self._graficar_auto())
            return e

        def grupo(texto, abierto=False):
            """Crea una sección colapsable y devuelve su `.body` para llenarla."""
            sec = SeccionColapsable(p, texto, abierto=abierto,
                                    on_toggle=self._on_frame_configure)
            sec.pack(fill=tk.X, pady=2)
            self._secciones.append(sec)
            return sec.body

        def opcion_menu(parent, var, *opciones, row, col, **grid_kw):
            """OptionMenu que re-grafica al cambiar."""
            m = tk.OptionMenu(parent, var, *opciones)
            m.config(bg=ENTRY, fg=FG, activebackground=BORDE,
                     activeforeground=FG, relief="flat",
                     font=("Consolas", 9), highlightthickness=0)
            m["menu"].config(bg=ENTRY, fg=FG, font=("Consolas", 9))
            m.grid(row=row, column=col, sticky="ew", **grid_kw)
            # trace_add: llama a _graficar_auto cada vez que la variable cambia
            var.trace_add("write", lambda *_: self._graficar_auto())
            return m

        # ── Botón abrir ───────────────────────────────────────────────────────
        tk.Button(p, text="📂  Abrir CSV", command=self._abrir,
                  bg=ACENT, fg=BG, font=("Consolas", 10, "bold"),
                  relief="flat", cursor="hand2", pady=6
                  ).pack(fill=tk.X, pady=(0, 4))

        self.var_archivo = tk.StringVar(value="Sin archivo")
        tk.Label(p, textvariable=self.var_archivo, bg=BG, fg=GRIS,
                 font=("Consolas", 8), wraplength=250, justify="left"
                 ).pack(anchor="w", pady=(0, 4))

        # ── Expandir / colapsar todo ──────────────────────────────────────────
        barra_sec = tk.Frame(p, bg=BG)
        barra_sec.pack(fill=tk.X, pady=(0, 4))
        tk.Button(barra_sec, text="▼ Expandir todo",
                  command=lambda: self._set_todas_secciones(True),
                  bg=ENTRY, fg=FG, font=("Consolas", 8), relief="flat",
                  cursor="hand2").pack(side=tk.LEFT, expand=True, fill=tk.X,
                                       padx=(0, 2))
        tk.Button(barra_sec, text="▶ Colapsar todo",
                  command=lambda: self._set_todas_secciones(False),
                  bg=ENTRY, fg=FG, font=("Consolas", 8), relief="flat",
                  cursor="hand2").pack(side=tk.LEFT, expand=True, fill=tk.X,
                                       padx=(2, 0))

        # ── Escala de unidades ───────────────────────────────── (abierta) ────
        c = grupo("Escala de unidades", abierto=True)

        lbl(c, "Eje X:").grid(row=0, column=0, sticky="w")
        self.var_esc_x = tk.StringVar(value="1e6  (s → µs)")
        opcion_menu(c, self.var_esc_x,
                    "1    (sin cambio)", "1e3  (s → ms)", "1e6  (s → µs)",
                    row=0, col=1)

        lbl(c, "Eje Y:").grid(row=1, column=0, sticky="w", pady=(4,0))
        self.var_esc_y = tk.StringVar(value="1    (sin cambio)")
        opcion_menu(c, self.var_esc_y,
                    "1    (sin cambio)", "1e3  (V → mV)",
                    row=1, col=1, pady=(4,0))
        c.columnconfigure(1, weight=1)

        # ── Tipo de escala ────────────────────────────────────────────────────
        c = grupo("Tipo de escala")

        lbl(c, "Eje X:").grid(row=0, column=0, sticky="w")
        self.var_tipo_x = tk.StringVar(value="linear")
        opcion_menu(c, self.var_tipo_x, "linear", "log", "symlog",
                    row=0, col=1)

        lbl(c, "Eje Y:").grid(row=1, column=0, sticky="w", pady=(4,0))
        self.var_tipo_y = tk.StringVar(value="linear")
        opcion_menu(c, self.var_tipo_y, "linear", "log", "symlog",
                    row=1, col=1, pady=(4,0))
        c.columnconfigure(1, weight=1)

        # ── Grilla ────────────────────────────────────────────────────────────
        c = grupo("Grilla")

        self.var_grilla = tk.BooleanVar(value=True)
        self.var_grilla.trace_add("write", lambda *_: self._graficar_auto())
        tk.Checkbutton(c, text="Mostrar grilla", variable=self.var_grilla,
                       bg=BG, fg=FG, selectcolor=ENTRY,
                       activebackground=BG, font=("Consolas", 9)
                       ).grid(row=0, column=0, columnspan=2, sticky="w")

        lbl(c, "Sep. X:").grid(row=1, column=0, sticky="w", pady=(4,0))
        self.e_sep_x = entry_num(c, 20)
        self.e_sep_x.grid(row=1, column=1, sticky="ew", pady=(4,0))

        lbl(c, "Sep. Y:").grid(row=2, column=0, sticky="w", pady=2)
        self.e_sep_y = entry_num(c, 0.5)
        self.e_sep_y.grid(row=2, column=1, sticky="ew", pady=2)
        c.columnconfigure(1, weight=1)

        # ── Límites ───────────────────────────────────────────────────────────
        c = grupo("Límites (vacío = auto)")

        for fila, (txt, attr) in enumerate([
            ("X mín:", "e_xmin"), ("X máx:", "e_xmax"),
            ("Y mín:", "e_ymin"), ("Y máx:", "e_ymax"),
        ]):
            lbl(c, txt).grid(row=fila, column=0, sticky="w", pady=1)
            e = entry_num(c)
            e.grid(row=fila, column=1, sticky="ew", pady=1)
            setattr(self, attr, e)
        c.columnconfigure(1, weight=1)

        # ── Márgenes ──────────────────────────────────────────────────────────
        c = grupo("Márgenes [%]")

        lbl(c, "Margen X:").grid(row=0, column=0, sticky="w")
        self.e_margen_x = entry_num(c, 3)
        self.e_margen_x.grid(row=0, column=1, sticky="ew")

        lbl(c, "Margen Y:").grid(row=1, column=0, sticky="w", pady=(4,0))
        self.e_margen_y = entry_num(c, 3)
        self.e_margen_y.grid(row=1, column=1, sticky="ew", pady=(4,0))
        c.columnconfigure(1, weight=1)

        # ── Colores de canal ──────────────────────────────────────────────────
        c = grupo("Color por canal")

        self.vars_color  = []   # StringVar con el hex actual
        self._btns_color = []   # botones de muestra de color

        for i in range(4):
            lbl(c, f"CH{i+1}:").grid(row=i, column=0, sticky="w", pady=2)

            var = tk.StringVar(value=COLORES_DEFAULT[i])
            self.vars_color.append(var)

            # Botón cuadrado que muestra el color actual y abre el selector
            btn = tk.Button(c, bg=COLORES_DEFAULT[i], width=3, relief="flat",
                            cursor="hand2",
                            command=lambda idx=i: self._elegir_color_canal(idx))
            btn.grid(row=i, column=1, sticky="w", padx=(0,4), pady=2)
            self._btns_color.append(btn)

            # Label con el valor hex
            tk.Label(c, textvariable=var, bg=BG, fg=GRIS,
                     font=("Consolas", 8)).grid(row=i, column=2, sticky="w")

        c.columnconfigure(2, weight=1)

        # ── Color de fondo ────────────────────────────────────────────────────
        c = grupo("Fondo del gráfico")

        # Fondo exterior (Figure)
        lbl(c, "Exterior:").grid(row=0, column=0, sticky="w", pady=2)
        self._btn_fondo_fig = tk.Button(
            c, bg=self.color_fondo_fig, width=3, relief="flat",
            cursor="hand2", command=self._elegir_fondo_fig)
        self._btn_fondo_fig.grid(row=0, column=1, sticky="w", pady=2)
        self.var_fondo_fig = tk.StringVar(value=self.color_fondo_fig)
        tk.Label(c, textvariable=self.var_fondo_fig, bg=BG, fg=GRIS,
                 font=("Consolas", 8)).grid(row=0, column=2, sticky="w")

        # Fondo del área del plot (Axes)
        lbl(c, "Plot:").grid(row=1, column=0, sticky="w", pady=2)
        self._btn_fondo_ax = tk.Button(
            c, bg=self.color_fondo_ax, width=3, relief="flat",
            cursor="hand2", command=self._elegir_fondo_ax)
        self._btn_fondo_ax.grid(row=1, column=1, sticky="w", pady=2)
        self.var_fondo_ax = tk.StringVar(value=self.color_fondo_ax)
        tk.Label(c, textvariable=self.var_fondo_ax, bg=BG, fg=GRIS,
                 font=("Consolas", 8)).grid(row=1, column=2, sticky="w")

        c.columnconfigure(2, weight=1)

        # ── Textos ────────────────────────────────────────────────────────────
        c = grupo("Textos")

        for fila, (txt, attr, val) in enumerate([
            ("Título:", "e_titulo",  "Señal medida"),
            ("Eje X:",  "e_label_x", "Tiempo [µs]"),
            ("Eje Y:",  "e_label_y", "Tensión [V]"),
        ]):
            lbl(c, txt).grid(row=fila, column=0, sticky="w", pady=1)
            e = tk.Entry(c, bg=ENTRY, fg=FG, insertbackground=FG,
                         relief="flat", font=("Consolas", 9), width=15)
            e.insert(0, val)
            e.bind("<FocusOut>", lambda _: self._graficar_auto())
            e.bind("<Return>",   lambda _: self._graficar_auto())
            e.grid(row=fila, column=1, sticky="ew", pady=1)
            setattr(self, attr, e)
        c.columnconfigure(1, weight=1)

        # ── Botones acción ────────────────────────────────────────────────────
        tk.Button(p, text="▶  Aplicar / Graficar", command=self._graficar,
                  bg=VERDE, fg=BG, font=("Consolas", 10, "bold"),
                  relief="flat", cursor="hand2", pady=8
                  ).pack(fill=tk.X, pady=(12, 3))

        tk.Button(p, text="💾  Guardar imagen", command=self._guardar,
                  bg=ENTRY, fg=FG, font=("Consolas", 9),
                  relief="flat", cursor="hand2", pady=5
                  ).pack(fill=tk.X, pady=3)

        # Estado
        self.var_estado = tk.StringVar(value="Listo.")
        tk.Label(p, textvariable=self.var_estado, bg=BG, fg=GRIS,
                 font=("Consolas", 8), wraplength=250,
                 justify="left", anchor="w"
                 ).pack(fill=tk.X, pady=(8, 4))

    def _set_todas_secciones(self, abrir: bool):
        """Abre o cierra todas las secciones colapsables de una vez."""
        for sec in self._secciones:
            if sec.abierto != abrir:
                sec.toggle()
        self._on_frame_configure()

    # =========================================================================
    # GRÁFICO
    # =========================================================================
    def _construir_grafico(self):
        self.fig = Figure(figsize=(8, 5), dpi=100,
                          facecolor=self.color_fondo_fig)
        self.ax  = self.fig.add_subplot(111, facecolor=self.color_fondo_ax)
        self._tema_ejes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.panel_graf)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True,
                                          padx=4, pady=4)

        frame_tb = tk.Frame(self.panel_graf, bg=BG)
        frame_tb.pack(fill=tk.X)
        NavigationToolbar2Tk(self.canvas, frame_tb).update()

        self._placeholder()

    def _tema_ejes(self):
        ax = self.ax
        ax.set_facecolor(self.color_fondo_ax)
        ax.tick_params(colors=FG)
        ax.xaxis.label.set_color(FG)
        ax.yaxis.label.set_color(FG)
        ax.title.set_color(FG)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDE)

    def _placeholder(self):
        self.ax.text(0.5, 0.5,
                     "Abrí un CSV para comenzar\n(Archivo → Abrir CSV  o  Ctrl+O)",
                     ha="center", va="center",
                     transform=self.ax.transAxes,
                     color=GRIS, fontsize=11, fontfamily="Consolas")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    # =========================================================================
    # ACTUALIZACIÓN AUTOMÁTICA (debounce)
    # =========================================================================
    def _graficar_auto(self):
        """
        Versión con debounce de _graficar: cancela el timer anterior
        y programa uno nuevo 300 ms después. Así si el usuario cambia
        varios controles rápido solo se re-grafica una vez al final.
        """
        if self.tiempo is None:
            return
        if self._timer_id is not None:
            self.root.after_cancel(self._timer_id)
        self._timer_id = self.root.after(300, self._graficar)

    # =========================================================================
    # SELECTORES DE COLOR
    # =========================================================================
    def _elegir_color_canal(self, idx: int):
        """Abre el selector de color del SO y actualiza el canal."""
        # colorchooser.askcolor devuelve ((r,g,b), "#rrggbb") o (None,None)
        _, hex_color = colorchooser.askcolor(
            color=self.vars_color[idx].get(),
            title=f"Color para CH{idx+1}"
        )
        if hex_color:
            self.vars_color[idx].set(hex_color)
            self._btns_color[idx].config(bg=hex_color)
            self._graficar_auto()

    def _elegir_fondo_fig(self):
        _, hex_color = colorchooser.askcolor(
            color=self.color_fondo_fig, title="Color de fondo exterior"
        )
        if hex_color:
            self.color_fondo_fig = hex_color
            self.var_fondo_fig.set(hex_color)
            self._btn_fondo_fig.config(bg=hex_color)
            self.fig.set_facecolor(hex_color)
            self._graficar_auto()

    def _elegir_fondo_ax(self):
        _, hex_color = colorchooser.askcolor(
            color=self.color_fondo_ax, title="Color del área del plot"
        )
        if hex_color:
            self.color_fondo_ax = hex_color
            self.var_fondo_ax.set(hex_color)
            self._btn_fondo_ax.config(bg=hex_color)
            self._graficar_auto()

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _float_entry(self, e: tk.Entry, nombre: str):
        t = e.get().strip()
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            raise ValueError(f"'{nombre}' no es un número válido: '{t}'")

    def _escala(self, var: tk.StringVar) -> float:
        return float(var.get().split()[0])

    # =========================================================================
    # ABRIR CSV
    # =========================================================================
    def _abrir(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not ruta:
            return

        ruta = Path(ruta)
        if ruta.suffix.lower() != ".csv":
            messagebox.showerror("Formato incorrecto",
                                 f"'{ruta.name}' no es un CSV.")
            return

        df = leer_datos(ruta)
        if df is None:
            messagebox.showerror("Error de lectura",
                                 f"No se pudo leer '{ruta.name}'.")
            return

        self.tiempo, self.channel = guardar_datos(df)
        self.var_archivo.set(ruta.name)
        n_ch, n_m = self.channel.shape
        self.var_estado.set(f"✓ {n_ch} canal(es) · {n_m} muestras")
        self._graficar()

    # =========================================================================
    # GRAFICAR
    # =========================================================================
    def _graficar(self):
        if self.tiempo is None:
            messagebox.showwarning("Sin datos", "Primero abrí un archivo CSV.")
            return

        try:
            esc_x    = self._escala(self.var_esc_x)
            esc_y    = self._escala(self.var_esc_y)
            sep_x    = self._float_entry(self.e_sep_x,    "Sep. X")    or 1.0
            sep_y    = self._float_entry(self.e_sep_y,    "Sep. Y")    or 1.0
            margen_x = self._float_entry(self.e_margen_x, "Margen X")  or 3.0
            margen_y = self._float_entry(self.e_margen_y, "Margen Y")  or 3.0
            x_min    = self._float_entry(self.e_xmin, "X mín")
            x_max    = self._float_entry(self.e_xmax, "X máx")
            y_min    = self._float_entry(self.e_ymin, "Y mín")
            y_max    = self._float_entry(self.e_ymax, "Y máx")
        except ValueError as e:
            messagebox.showerror("Parámetro inválido", str(e))
            return

        tipo_x  = self.var_tipo_x.get()
        tipo_y  = self.var_tipo_y.get()
        grilla  = self.var_grilla.get()
        titulo  = self.e_titulo.get()
        label_x = self.e_label_x.get()
        label_y = self.e_label_y.get()
        colores = [v.get() for v in self.vars_color]

        # Límites automáticos con buscar_limites_transitorio
        if any(v is None for v in (x_min, x_max, y_min, y_max)):
            try:
                xa, xb, ya, yb = buscar_limites_transitorio(
                    tiempo=self.tiempo, channel=self.channel,
                    canal_referencia=0,
                    escala_eje_x=esc_x, escala_eje_y=esc_y,
                )
                x_min = x_min if x_min is not None else xa
                x_max = x_max if x_max is not None else xb
                y_min = y_min if y_min is not None else ya
                y_max = y_max if y_max is not None else yb
            except Exception:
                tg = self.tiempo  * esc_x
                cg = self.channel * esc_y
                x_min = x_min if x_min is not None else float(np.nanmin(tg))
                x_max = x_max if x_max is not None else float(np.nanmax(tg))
                y_min = y_min if y_min is not None else float(np.nanmin(cg))
                y_max = y_max if y_max is not None else float(np.nanmax(cg))

        try:
            x_min_g, x_max_g = agregar_margen_porcentual(
                x_min, x_max, margen_x, tipo_x)
            y_min_g, y_max_g = agregar_margen_porcentual(
                y_min, y_max, margen_y, tipo_y)
        except ValueError as e:
            messagebox.showerror("Error de límites", str(e))
            return

        # Actualizar colores de fondo antes de dibujar
        self.fig.set_facecolor(self.color_fondo_fig)
        self.ax.cla()
        self._tema_ejes()

        aplicar_curva(
            fig=self.fig, ax=self.ax,
            tiempo_grafico=self.tiempo * esc_x,
            channel_grafico=self.channel * esc_y,
            x_min_grafico=x_min_g, x_max_grafico=x_max_g,
            y_min_grafico=y_min_g, y_max_grafico=y_max_g,
            escala_graf_x=tipo_x, escala_graf_y=tipo_y,
            sep_x=sep_x, sep_y=sep_y,
            title=titulo, unidad_x=label_x, unidad_y=label_y,
            mostrar_grilla=grilla,
            colores=colores,
        )

        self._tema_ejes()
        self.ax.legend(facecolor=ENTRY, edgecolor=BORDE, labelcolor=FG)
        self.ax.tick_params(colors=FG)
        self.canvas.draw()

        n_ch = self.channel.shape[0]
        self.var_estado.set(
            f"✓ {n_ch} canal(es) | X: {tipo_x} | Y: {tipo_y}"
        )

    # =========================================================================
    # GUARDAR
    # =========================================================================
    def _guardar(self):
        if self.tiempo is None:
            messagebox.showwarning("Sin gráfico", "Primero graficá una señal.")
            return
        ruta = filedialog.asksaveasfilename(
            title="Guardar imagen",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
            initialfile="grafico_osciloscopio"
        )
        if not ruta:
            return
        self.fig.savefig(ruta, dpi=300, bbox_inches="tight",
                         facecolor=self.fig.get_facecolor())
        self.var_estado.set(f"✓ Guardado: {Path(ruta).name}")
        messagebox.showinfo("Guardado", f"Imagen guardada en:\n{ruta}")


# ─── Punto de entrada ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    OscilloscopeGUI(root)
    root.mainloop()
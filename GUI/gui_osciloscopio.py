import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import os

# ── Drag & Drop: usar TkinterDnD.Tk si está instalado, si no tk.Tk normal ──
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _BaseClass = TkinterDnD.Tk
    _DND_AVAILABLE = True
except ImportError:
    _BaseClass = tk.Tk
    _DND_AVAILABLE = False

# ──────────────────────────────────────────────────────────────────────────────
CHANNEL_COLORS = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"]
CHANNEL_LABELS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6"]

BG_DARK  = "#1a1a2e"
BG_MID   = "#16213e"
BG_PANEL = "#0f3460"
ACCENT   = "#e94560"
FG_TEXT  = "#eaeaea"
FG_DIM   = "#8899aa"


def auto_scale_time(t_seconds):
    max_abs = np.max(np.abs(t_seconds))
    if max_abs == 0:
        return t_seconds, "Tiempo [s]"
    if max_abs < 1e-6:
        return t_seconds * 1e9, "Tiempo [ns]"
    if max_abs < 1e-3:
        return t_seconds * 1e6, "Tiempo [µs]"
    if max_abs < 1:
        return t_seconds * 1e3, "Tiempo [ms]"
    return t_seconds, "Tiempo [s]"


def load_oscilloscope_csv(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        line1 = f.readline().strip()
        f.readline()  # línea 2 (unidades)

    sep = "\t" if "\t" in line1 else ","

    first_col = line1.split(sep)[0].strip().lower()
    if "x" not in first_col and "time" not in first_col and "axis" not in first_col:
        raise ValueError(
            "El archivo no tiene el formato esperado de osciloscopio.\n"
            f"Primera celda encontrada: '{first_col}'"
        )

    df = pd.read_csv(path, sep=sep, skiprows=2, header=None)
    df = df.dropna(axis=1, how="all")

    if df.shape[1] < 2:
        raise ValueError("El CSV no tiene suficientes columnas de datos.")

    time = df.iloc[:, 0].astype(float).values
    channels = {}
    for i in range(df.shape[1] - 1):
        label = CHANNEL_LABELS[i] if i < len(CHANNEL_LABELS) else f"CH{i+1}"
        channels[label] = df.iloc[:, i + 1].astype(float).values

    return time, channels


def load_bode_csv(path):
    """
    Lee un CSV de Bode y agrupa múltiples canales (ganancia y fase) de forma dinámica.
    """
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("No se pudo decodificar el archivo CSV de Bode.")

    df.columns = df.columns.str.strip()

    freq_col = next((c for c in df.columns if "frequency" in c.lower()), None)
    if freq_col is None:
        raise ValueError("No se encontró columna de Frecuencia.")
    
    freq = pd.to_numeric(df[freq_col], errors="coerce").values.astype(float)

    # Buscar todas las columnas que parezcan ganancias y fases
    gain_cols = [c for c in df.columns if "gain" in c.lower() or "db" in c.lower()]
    phase_cols = [c for c in df.columns if "phase" in c.lower()]

    if not gain_cols:
        raise ValueError("No se encontraron columnas de Ganancia en el archivo.")

    channels = {}
    for i, g_col in enumerate(gain_cols):
        label = CHANNEL_LABELS[i] if i < len(CHANNEL_LABELS) else f"CH{i+1}"
        p_col = phase_cols[i] if i < len(phase_cols) else None
        
        gain_data = pd.to_numeric(df[g_col], errors="coerce").values.astype(float)
        phase_data = pd.to_numeric(df[p_col], errors="coerce").values.astype(float) if p_col else None
        
        # Guardamos diccionarios por canal para el bode
        channels[label] = {"gain": gain_data, "phase": phase_data}

    return freq, channels


def _is_bode_csv(path):
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=enc, nrows=0)
            df.columns = df.columns.str.strip()
            cols = " ".join(df.columns).lower()
            return any(kw in cols for kw in ("frequency", "gain", "phase", " db"))
        except UnicodeDecodeError:
            continue
        except Exception:
            return False
    return False


# ──────────────────────────────────────────────────────────────────────────────
class OscilloscopeGUI(_BaseClass):
    def __init__(self):
        super().__init__()
        self.title("Visualizador de Osciloscopio — TP Final TC1")
        self.geometry("1280x780")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        self.time_raw  = None      # Se usa tanto para tiempo (osc) como frecuencia (bode)
        self.channels  = {}        # Diccionario de canales
        self.ch_vars   = {}        # Variables de UI de los canales
        self.file_path = None

        self._mode     = "osc"     # "osc" | "bode"

        self._build_ui()
        self._setup_dnd()

        self.var_grid.trace_add("write",    lambda *_: self._plot())
        self.var_logy.trace_add("write",    lambda *_: self._plot())
        self.var_markers.trace_add("write", lambda *_: self._plot())

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        topbar = tk.Frame(self, bg=BG_PANEL, height=52)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="📡  Visualizador de Osciloscopio",
                 bg=BG_PANEL, fg=FG_TEXT,
                 font=("Helvetica", 14, "bold")).pack(side="left", padx=16, pady=12)

        self.lbl_file = tk.Label(topbar, text="Ningún archivo cargado",
                                  bg=BG_PANEL, fg=FG_DIM, font=("Helvetica", 10))
        self.lbl_file.pack(side="left", padx=8)

        tk.Button(topbar, text="Abrir CSV", bg=ACCENT, fg="white",
                  font=("Helvetica", 10, "bold"), relief="flat",
                  padx=14, pady=6, cursor="hand2",
                  command=self._open_file).pack(side="right", padx=16, pady=8)

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=BG_MID, width=270)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        self.plot_frame = tk.Frame(body, bg=BG_DARK)
        self.plot_frame.pack(side="left", fill="both", expand=True)

        self.fig = Figure(figsize=(9, 5), facecolor="#0d1117")
        self.ax  = self.fig.add_subplot(111)
        self._style_axes(self.ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar_frame = tk.Frame(self.plot_frame, bg="#0d1117")
        toolbar_frame.pack(fill="x")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.config(background="#0d1117")
        toolbar.update()

        dnd_hint = "Arrastrá un CSV aquí\n\no hacé clic para abrir" if _DND_AVAILABLE \
                   else "📂\n\nHacé clic aquí para abrir un CSV\n\no usá el botón  «Abrir CSV»"

        self._drop_frame = tk.Frame(self.plot_frame, bg="#0d1117")
        self._drop_frame.place(relx=0.5, rely=0.5, anchor="center")

        self._drop_label = tk.Label(
            self._drop_frame, text=dnd_hint,
            bg="#111c2b", fg=FG_DIM, font=("Helvetica", 15),
            justify="center", padx=40, pady=30,
            cursor="hand2", relief="groove", bd=2
        )
        self._drop_label.pack()
        self._drop_label.bind("<Button-1>", lambda e: self._open_file())
        self._drop_label.bind("<Enter>",
            lambda e: self._drop_label.configure(fg=FG_TEXT, bg="#1a2a40"))
        self._drop_label.bind("<Leave>",
            lambda e: self._drop_label.configure(fg=FG_DIM, bg="#111c2b"))

    def _build_sidebar(self):
        sb = self.sidebar
        tk.Label(sb, text="Controles", bg=BG_MID, fg=FG_TEXT,
                 font=("Helvetica", 12, "bold")).pack(pady=(14, 6), padx=12, anchor="w")
        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=8, pady=4)

        opts_frame = tk.Frame(sb, bg=BG_MID)
        opts_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(opts_frame, text="Opciones globales", bg=BG_MID, fg=FG_DIM,
                 font=("Helvetica", 9, "bold")).grid(row=0, column=0, columnspan=2,
                                                      sticky="w", pady=(0, 6))
        self.var_grid    = tk.BooleanVar(value=True)
        self.var_logy    = tk.BooleanVar(value=False)
        self.var_markers = tk.BooleanVar(value=False)
        self._chk(opts_frame, "Mostrar grilla",  self.var_grid,    1)
        self._chk(opts_frame, "Escala log en Y", self.var_logy,    2)
        self._chk(opts_frame, "Marcar máx/mín",  self.var_markers, 3)

        tk.Label(sb, text="Título del gráfico", bg=BG_MID, fg=FG_DIM,
                 font=("Helvetica", 9)).pack(anchor="w", padx=12, pady=(10, 2))
        self.var_title = tk.StringVar(value="Señal de osciloscopio")
        self.var_title.trace_add("write", lambda *_: self._plot())
        self.entry_title = tk.Entry(sb, textvariable=self.var_title,
                                    bg="#1e2a3a", fg=FG_TEXT,
                                    insertbackground=FG_TEXT,
                                    relief="flat", font=("Helvetica", 10))
        self.entry_title.pack(fill="x", padx=12, pady=(0, 6))

        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=8, pady=8)
        tk.Label(sb, text="Canales", bg=BG_MID, fg=FG_TEXT,
                 font=("Helvetica", 11, "bold")).pack(anchor="w", padx=12)

        canvas_ch = tk.Canvas(sb, bg=BG_MID, highlightthickness=0)
        scrollbar = ttk.Scrollbar(sb, orient="vertical", command=canvas_ch.yview)
        self.ch_frame = tk.Frame(canvas_ch, bg=BG_MID)
        self.ch_frame.bind("<Configure>",
            lambda e: canvas_ch.configure(scrollregion=canvas_ch.bbox("all")))
        canvas_ch.create_window((0, 0), window=self.ch_frame, anchor="nw")
        canvas_ch.configure(yscrollcommand=scrollbar.set)
        canvas_ch.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _chk(self, parent, text, variable, row):
        tk.Checkbutton(parent, text=text, variable=variable,
                       bg=BG_MID, fg=FG_TEXT, selectcolor=BG_PANEL,
                       activebackground=BG_MID, activeforeground=FG_TEXT,
                       font=("Helvetica", 9)
                       ).grid(row=row, column=0, columnspan=2, sticky="w", pady=1)

    def _build_channel_controls(self):
        for widget in self.ch_frame.winfo_children():
            widget.destroy()

        for idx, label in enumerate(self.channels.keys()):
            color       = CHANNEL_COLORS[idx % len(CHANNEL_COLORS)]
            offset_var  = tk.DoubleVar(value=0.0)
            scale_var   = tk.DoubleVar(value=1.0)
            visible_var = tk.BooleanVar(value=True)
            offset_var.trace_add("write",  lambda *_: self._plot())
            scale_var.trace_add("write",   lambda *_: self._plot())
            visible_var.trace_add("write", lambda *_: self._plot())
            self.ch_vars[label] = {
                "visible": visible_var,
                "color":   color,
                "offset":  offset_var,
                "scale":   scale_var,
            }
            self._build_ch_card(self.ch_frame, label, idx)

    def _build_ch_card(self, parent, label, idx):
        color = self.ch_vars[label]["color"]
        card  = tk.Frame(parent, bg=BG_PANEL, bd=0, relief="flat")
        card.pack(fill="x", padx=8, pady=4, ipadx=6, ipady=6)

        hdr = tk.Frame(card, bg=BG_PANEL)
        hdr.pack(fill="x")

        indicator = tk.Label(hdr, text="●", bg=BG_PANEL, fg=color,
                             font=("Helvetica", 14))
        indicator.pack(side="left", padx=(0, 4))

        tk.Checkbutton(hdr, text=label,
                       variable=self.ch_vars[label]["visible"],
                       bg=BG_PANEL, fg=FG_TEXT, selectcolor=BG_MID,
                       activebackground=BG_PANEL, activeforeground=FG_TEXT,
                       font=("Helvetica", 10, "bold")).pack(side="left")

        btn_color = tk.Button(hdr, text="Color", font=("Helvetica", 8),
                              bg=color, fg="white", relief="flat",
                              padx=6, pady=2, cursor="hand2",
                              command=lambda l=label, i=indicator: self._pick_color(l, i))
        btn_color.pack(side="right", padx=4)
        self.ch_vars[label]["color_btn"] = btn_color

        controls = tk.Frame(card, bg=BG_PANEL)
        controls.pack(fill="x", pady=(6, 0))
        self._labeled_entry(controls, "Offset [V/dB]:", self.ch_vars[label]["offset"], 0, 0)
        self._labeled_entry(controls, "Escala ×:",   self.ch_vars[label]["scale"],  1, 0)

    def _labeled_entry(self, parent, text, variable, row, col, width=7):
        tk.Label(parent, text=text, bg=BG_PANEL, fg=FG_DIM,
                 font=("Helvetica", 8)).grid(row=row, column=col, sticky="w", pady=1)
        tk.Entry(parent, textvariable=variable,
                 bg="#1e2a3a", fg=FG_TEXT, insertbackground=FG_TEXT,
                 relief="flat", font=("Helvetica", 9), width=width
                 ).grid(row=row, column=col+1, sticky="w", padx=(4, 0), pady=1)

    # ── Color picker ──────────────────────────────────────────────────────────

    def _pick_color(self, label, indicator_widget):
        from tkinter import colorchooser
        color = colorchooser.askcolor(color=self.ch_vars[label]["color"],
                                      title=f"Color — {label}")[1]
        if color:
            self.ch_vars[label]["color"] = color
            indicator_widget.configure(fg=color)
            self.ch_vars[label]["color_btn"].configure(bg=color)
            self._plot()

    # ── Archivo ───────────────────────────────────────────────────────────────

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if path:
            self._load(path)

    def _load(self, path):
        path = path.strip().strip("{}")
        if not os.path.isfile(path):
            messagebox.showerror("Error", f"El archivo no existe:\n{path}")
            return
        if not path.lower().endswith(".csv"):
            if not messagebox.askyesno("Advertencia",
                    f"{os.path.basename(path)} no es .csv. ¿Intentar de todos modos?"):
                return

        if _is_bode_csv(path):
            try:
                time_raw, channels = load_bode_csv(path)
            except Exception as e:
                messagebox.showerror("Archivo inválido", f"No se pudo cargar el Bode:\n{e}")
                return
            self._mode = "bode"
        else:
            try:
                time_raw, channels = load_oscilloscope_csv(path)
            except (ValueError, pd.errors.ParserError, UnicodeDecodeError, KeyError) as e:
                messagebox.showerror("Archivo inválido", f"No se pudo cargar el archivo.\n\n{e}")
                return
            except Exception as e:
                messagebox.showerror("Error inesperado", str(e))
                return
            self._mode = "osc"

        self.time_raw = time_raw
        self.channels = channels
        self.file_path = path
        
        self.lbl_file.configure(text=f"📄 {os.path.basename(path)}", fg=FG_TEXT)
        nombre_sin_ext = os.path.splitext(os.path.basename(path))[0]
        self.var_title.set(nombre_sin_ext)
        self._drop_frame.place_forget()
        self._build_channel_controls()
        self._plot()

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    def _setup_dnd(self):
        if not _DND_AVAILABLE:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", lambda e: self._load(e.data))
        except Exception:
            pass

    # ── Gráfico: dispatcher ───────────────────────────────────────────────────

    def _plot(self):
        if self._mode == "bode":
            self._plot_bode()
        else:
            self._plot_oscilloscope()

    # ── Bode ──────────────────────────────────────────────────────────────────

    def _plot_bode(self):
        if self.time_raw is None:
            return

        freq = self.time_raw
        self.fig.clear()

        ax1 = self.fig.add_subplot(111)
        self._style_axes(ax1)

        title    = self.var_title.get().strip() or "Diagrama de Bode"
        grid_kw  = dict(color="#2a3a50", linewidth=0.6, linestyle="--", which="both")

        ax1.set_ylabel("Ganancia [dB]", color=FG_TEXT, fontsize=10)
        ax1.set_xlabel("Frecuencia [Hz]", color=FG_DIM, fontsize=10)
        ax1.set_title(title, color=FG_TEXT, fontsize=12, pad=10)
        ax1.grid(self.var_grid.get(), **grid_kw)
        
        # Referencia fija en -3dB
        ax1.axhline(-3, color=FG_DIM, linestyle="--", linewidth=1, label="−3 dB")

        # Configurar el eje secundario (twinx) para la Fase
        ax2 = ax1.twinx()
        self._style_axes(ax2)
        ax2.patch.set_visible(False)  # Fundamental para no tapar la grilla de ax1
        ax2.set_ylabel("Fase [°]", color=FG_TEXT, fontsize=10)

        lines, labels = [], []
        # Capturamos la línea de -3dB para la leyenda unificada
        h, l = ax1.get_legend_handles_labels()
        lines.extend(h)
        labels.extend(l)

        for label, data in self.channels.items():
            v = self.ch_vars.get(label)
            if v is None or not v["visible"].get():
                continue
            
            color = v["color"]
            try:
                scale  = float(v["scale"].get())
                offset = float(v["offset"].get())
            except (tk.TclError, ValueError):
                scale, offset = 1.0, 0.0

            # Procesamiento de la Ganancia
            gain = data["gain"] * scale + offset
            l1, = ax1.semilogx(freq, gain, color=color, linestyle="-", linewidth=1.8, label=f"Gan. {label}")
            lines.append(l1)
            labels.append(f"Gan. {label}")

            # Procesamiento de la Fase (si el archivo la tiene)
            if data["phase"] is not None:
                phase = data["phase"] * scale + offset
                l2, = ax2.semilogx(freq, phase, color=color, linestyle="--", linewidth=1.8, label=f"Fase {label}")
                lines.append(l2)
                labels.append(f"Fase {label}")

        ax1.legend(lines, labels, facecolor=BG_PANEL, edgecolor="#445566", labelcolor=FG_TEXT, fontsize=9)

        self.fig.tight_layout()
        self.canvas.draw()

    # ── Osciloscopio ──────────────────────────────────────────────────────────

    def _plot_oscilloscope(self):
        if self.time_raw is None:
            return

        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self._style_axes(self.ax)
        t, t_label = auto_scale_time(self.time_raw)
        title = self.var_title.get().strip() or "Señal de osciloscopio"

        visible_data = {}
        for label, data in self.channels.items():
            v = self.ch_vars.get(label)
            if v is None or not v["visible"].get():
                continue
            try:
                scale  = float(v["scale"].get())
                offset = float(v["offset"].get())
            except (tk.TclError, ValueError):
                scale, offset = 1.0, 0.0
            y_base = data * scale + offset
            visible_data[label] = {"y_base": y_base, "color": v["color"]}

        if not visible_data:
            self.canvas.draw()
            return

        shift = 0.0
        is_log_shifted = False
        if self.var_logy.get():
            y_min_global = min(np.min(d["y_base"]) for d in visible_data.values())
            if y_min_global <= 0:
                shift = abs(y_min_global) + 0.001
                is_log_shifted = True

        y_label = "Tensión [V]"
        factor_y = 1.0
        max_abs_y = max(np.max(np.abs(d["y_base"] + shift)) for d in visible_data.values())
        if max_abs_y > 0:
            if max_abs_y < 1e-3:
                factor_y, y_label = 1e6, "Tensión [µV]"
            elif max_abs_y < 1:
                factor_y, y_label = 1e3, "Tensión [mV]"
        if is_log_shifted:
            y_label += " (desplazada)"

        for label, d in visible_data.items():
            y_final = (d["y_base"] + shift) * factor_y
            color = d["color"]
            self.ax.plot(t, y_final, color=color, linewidth=1.4, label=label)

            if self.var_markers.get():
                i_max = np.argmax(y_final)
                i_min = np.argmin(y_final)
                self.ax.plot(t[i_max], y_final[i_max], "^", color=color, markersize=8)
                self.ax.axvline(t[i_max], color=color, linewidth=0.6, linestyle=":")
                self.ax.text(t[i_max], y_final[i_max], f"  MAX {y_final[i_max]:.3g}",
                             color=color, fontsize=7.5, va="bottom")
                self.ax.plot(t[i_min], y_final[i_min], "v", color=color, markersize=8)
                self.ax.axvline(t[i_min], color=color, linewidth=0.6, linestyle=":")
                self.ax.text(t[i_min], y_final[i_min], f"  MIN {y_final[i_min]:.3g}",
                             color=color, fontsize=7.5, va="top")

        self.ax.set_title(title, color=FG_TEXT, fontsize=12, pad=10)
        self.ax.set_xlabel(t_label, color=FG_DIM, fontsize=10)
        self.ax.set_ylabel(y_label, color=FG_DIM, fontsize=10)

        if self.var_logy.get():
            try:
                self.ax.set_yscale("log")
            except Exception:
                pass

        self.ax.grid(self.var_grid.get(), color="#2a3a50", linewidth=0.6, linestyle="--")
        self.ax.legend(facecolor=BG_PANEL, edgecolor="#445566", labelcolor=FG_TEXT, fontsize=9)
        self.canvas.draw()

    def _style_axes(self, ax):
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors=FG_DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#2a3a50")


if __name__ == "__main__":
    app = OscilloscopeGUI()
    app.mainloop()

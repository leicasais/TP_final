# Visualizador de Osciloscopio y Bode — TP Final TC1
GUI en Python para visualizar archivos CSV exportados desde osciloscopios de laboratorio y diagramas de Bode.

---

## Requisitos

```bash
py -m pip install pandas matplotlib
```

Para habilitar el **drag & drop** de archivos (opcional):

```bash
py -m pip install tkinterdnd2
```

---

## Cómo ejecutar

```bash
py gui_osciloscopio.py
```

---

## Formatos de CSV soportados

El programa **detecta automáticamente** el tipo de archivo al cargarlo.

### Osciloscopio

El archivo debe tener el siguiente encabezado de dos líneas:

```
x-axis,1,2,3,4
second,Volt,Volt,Volt,Volt
-84.48E-06,0.0E+00,4.70E+00,4.99E+00,5.01E+00
...
```

- Primera fila: nombres de columnas (`x-axis`, `1`, `2`, ...)
- Segunda fila: unidades (`second`, `Volt`, ...) — se descarta automáticamente
- Resto: datos numéricos

Soporta archivos de **1 a 4 canales**. El separador puede ser `,` o tabulación.

### Bode

Formato exportado por el generador de funciones del laboratorio:

```
#, Frequency (Hz), Amplitude (Vpp), Gain (dB), Phase (°)
1,10.0,0.4000,-25.94,86.54
2,11.0,0.4000,-25.11,86.35
...
```

- El programa detecta automáticamente este formato por los nombres de columna
- Soporta el encoding `latin-1` usado por algunos equipos (símbolo `°`)
- La columna `Amplitude (Vpp)` se ignora; se grafican **Ganancia** y **Fase**

---

## Funcionalidades

### Generales
- Detección automática del tipo de CSV (osciloscopio o Bode)
- No crashea con archivos inválidos: muestra un mensaje de error
- Drag & Drop de archivos CSV (requiere `tkinterdnd2`)
- Título del gráfico editable (se inicializa con el nombre del archivo)
- Grilla configurable (mostrar/ocultar)

### Modo Osciloscopio
- Carga archivos CSV con cualquier número de canales (entre 1 y 4)
- Escala automática en el eje X (ns / µs / ms / s)
- Escala automática en el eje Y (µV / mV / V)
- Offset y escala (amplitud) ajustables por canal
- Color personalizable por canal
- Escala logarítmica en el eje Y (desplaza automáticamente si hay valores negativos)
- Marcadores de máximo y mínimo por canal

### Modo Bode
- Grafica Ganancia [dB] y Fase [°] en un único gráfico con doble eje Y
- Eje X en escala logarítmica (Hz)
- Línea de referencia en −3 dB

---

## Controles

### Controles globales (ambos modos)

| Control | Descripción |
|---|---|
| **Abrir CSV** | Abre el explorador para seleccionar un archivo |
| **Drag & Drop** | Arrastrá el CSV directo a la ventana |
| **Título** | Campo editable; el gráfico se actualiza mientras escribís |
| **Mostrar grilla** | Activa/desactiva la grilla |

### Solo Modo Osciloscopio

| Control | Descripción |
|---|---|
| **Escala log en Y** | Cambia el eje Y a escala logarítmica |
| **Marcar máx/mín** | Marca el punto máximo y mínimo de cada canal |
| **CH1–CH4** | Tilde para mostrar/ocultar cada canal |
| **Color** | Abre un selector de color para cada canal |
| **Offset [V]** | Desplaza verticalmente la curva del canal |
| **Escala ×** | Multiplica la amplitud de la curva del canal |

Todos los controles se aplican en tiempo real sin necesidad de confirmar.

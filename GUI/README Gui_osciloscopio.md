# Visualizador de Osciloscopio — TP Final TC1

GUI en Python para visualizar archivos CSV exportados desde osciloscopios de laboratorio.

---

## Requisitos

- Las siguientes librerías:

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

## Formato de CSV soportado

El archivo debe tener el siguiente encabezado de dos líneas:

```
x-axis,1,2,3,4
second,Volt,Volt,Volt,Volt
-84.48E-06,0.0E+00,4.70E+00,4.99E+00,5.01E+00
...
```

- Primera fila: nombres de columnas (`x-axis`, `1`, `2`, ...)
- Segunda fila: unidades (`second`, `Volt`, ...)
- Resto: datos numéricos

Soporta archivos de **1 a 4 canales**. El separador puede ser `,` o tabulación.

---

## Funcionalidades

- Carga archivos CSV con cualquier número de canales (Entre 1 y 4)
- Ejes con nombre y unidades
- Escala automática en ambos ejes (ns / µs / ms / s o nV / µV / mV / V)
- Título del gráfico editable (se inicializa con el nombre del archivo)
- Offset y escala (amplitud) ajustables por canal
- No crashea con archivos inválidos: muestra un mensaje de error
- Color personalizable por canal
- Grilla configurable (mostrar/ocultar)
- Escala logarítmica en el eje Y (desplaza automáticamente si hay valores negativos)
- Drag & Drop de archivos CSV (requiere `tkinterdnd2`)
- Marcadores de máximo y mínimo por canal

---

## Controles

| Control | Descripción |
|---|---|
| **Abrir CSV** | Abre el explorador para seleccionar un archivo |
| **Drag & Drop** | Arrastrá el CSV directo a la ventana |
| **Título** | Campo editable; el gráfico se actualiza mientras escribís |
| **Mostrar grilla** | Activa/desactiva la grilla |
| **Escala log en Y** | Cambia el eje Y a escala logarítmica |
| **Marcar máx/mín** | Marca el punto máximo y mínimo de cada canal |
| **CH1–CH4** | Tilde para mostrar/ocultar cada canal |
| **Color** | Abre un selector de color para cada canal |
| **Offset [V]** | Desplaza verticalmente la curva del canal |
| **Escala ×** | Multiplica la amplitud de la curva del canal |

Todos los controles se aplican en tiempo real sin necesidad de confirmar.

---

## Archivos

```
gui_osciloscopio.py       — Código principal de la GUI
muestra_osciloscopio.csv  — CSV de prueba con 4 canales (señales senoidales)
README.md                 — Este archivo
```

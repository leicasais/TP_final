from pathlib import Path
from func.manejo_datos import guardar_datos, leer_datos
from func.graficos import graficar_curva
from func.analisis_datos import info_relevante_csv, buscar_limites_transitorio
def main():
    #input
    archivo=Path("data/Carga.csv")   #mejorar input
    carpeta_salida = Path("output/graficos")

    #proceso de datos
    df = leer_datos(archivo)
    if df is not None:
        escala_eje_x = 1e6  # Convertir de segundos a microsegundos
        escala_eje_y=1
        tiempo, channel = guardar_datos(df) 
        (
            x_min,
            x_max,
            y_min,
            y_max
        ) = buscar_limites_transitorio(
            tiempo=tiempo,
            channel=channel,
            canal_referencia=0,
            escala_eje_x=escala_eje_x,
            escala_eje_y=escala_eje_y,
            tolerancia_final=5,
            muestras_estables=40
        ) 
        graficar_curva(
            tiempo=tiempo,
            channel=channel,
            ruta_salida="outputs/graficos/Carga_transitorio.png",

            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,

            escala_eje_x=escala_eje_x,
            escala_eje_y=escala_eje_y,

            sep_x=20,
            sep_y=0.5,

            margen_x=3,
            margen_y=5,

            title="Transitorio de carga",
            unidad_x="Tiempo [µs]",
            unidad_y="Tensión [V]"
        )
    else:
        print("No se pudieron leer los datos.")



if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np  

def leer_datos(archivo, skiprows=2, header=None, sep=","):    #formato(columnas): tiempo(0), CH1(1), CH2(2), ..., CHn(n) ; Por defecto lee arch csv del TP final
    try:
        df = pd.read_csv(archivo, skiprows=skiprows, header=header, sep=sep)
        return df
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None
    return df


def guardar_datos(df):  #df-> Dataframe del CSV ; tiempo-> vector, channel-> matriz (fila:columna = voltaje:canal)
    tiempo = df.iloc[:, 0].to_numpy()  
    channel = df.iloc[:, 1:].to_numpy().T 
    
    return tiempo, channel
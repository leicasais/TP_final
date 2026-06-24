 (instalar todas las librerias que quiero usar solo dentro de la carpeta de trabajo)

WINDOWS

Crear entorno:
$ python -m venv .venv

Activar entorno virtual: 
$ .\.venv\Scripts\Activate.ps1

Intalar Librerias requeridas para el proyecto en el entorno virtual: 
python -m pip install -r requirements.txt


macOS o Linux
crear entorno: 
$ python3 -m venv .venv

Activarlo:
$ source .venv/bin/activate

Instalar librerias: 
$ python3 -m pip install -r requirements.txt
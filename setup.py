import sys
from cx_Freeze import setup, Executable

# Definir las dependencias que se incluirán en el paquete
build_exe_options = {
    # CAMBIO: Se añaden 'duckdb' y 'pandas' como dependencias
    "packages": [
        "os", "sys", "psutil", "wmi", "configparser", "logging", 
        "pythoncom", "servicemanager", "duckdb", "pandas", "pyarrow" # pyarrow es necesario para pandas/parquet
    ],
    "excludes": ["tkinter"],
    "include_files": [
        ("configs", "configs"), # Incluye la carpeta configs
        ("data", "data"),        # Incluye la carpeta data (inicialmente vacía)
        ("libs", "libs"),       # Incluye la carpeta libs
    ],
}

# Configuración del servicio
executables = [
    Executable(
        "main.py",
        base=None,   # No se requiere una ventana de consola
        target_name="PythonMonitorAgent.exe",
        icon=None,
    )
]

setup(
    name="PythonMonitorAgent",
    version="1.0",
    description="An agent to monitor system resources using Python and save the metrics to Parquet files via DuckDB.",
    options={"build_exe": build_exe_options},
    executables=executables,
)

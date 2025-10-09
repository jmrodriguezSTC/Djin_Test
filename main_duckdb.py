import os
import logging
import pandas as pd
from datetime import datetime, timedelta
import duckdb

class ParquetManager:
    """
    Gestor de archivos Parquet que utiliza Pandas y DuckDB para la escritura
    y operaciones de sistema para la limpieza. Implementado como un Singleton 
    para asegurar una única instancia de gestión de archivos.
    """
    _instance = None
    _parquet_dir = None
    _retention_minutes = 60 # 1 hora por defecto

    def __new__(cls, parquet_dir=None):
        """
        Método mágico que controla la creación de la instancia Singleton.
        Asegura que solo se cree y configure una instancia.
        """
        if cls._instance is None:
            cls._instance = super(ParquetManager, cls).__new__(cls)
            if parquet_dir:
                cls._parquet_dir = parquet_dir
                cls._instance._setup_directory()
        return cls._instance

    def _setup_directory(self):
        """Asegura que el directorio de almacenamiento de Parquet exista (.\data\metricas)."""
        if self._parquet_dir:
            try:
                # Crea el directorio si no existe. 'exist_ok=True' previene errores si ya existe.
                os.makedirs(self._parquet_dir, exist_ok=True)
                logging.info(f"Directorio de Parquet asegurado: {self._parquet_dir}")
            except OSError as e:
                logging.error(f"Error al crear el directorio de Parquet {self._parquet_dir}: {e}")
                self._parquet_dir = None # Invalida la ruta si falla

    def save_metrics_to_parquet(self, data):
        """
        Convierte un diccionario de métricas en un DataFrame de una sola fila 
        y lo guarda como un archivo Parquet, nombrando el archivo con la 
        marca de tiempo de la métrica para una identificación única.

        :param data: Diccionario con la información de la métrica (debe contener 'timestamp').
        :return: True si se guardó correctamente, False en caso contrario.
        """
        if not self._parquet_dir:
            logging.warning("No se puede guardar el archivo Parquet. El directorio no está configurado o es inválido.")
            return False

        try:
            # 1. Preparación de los datos
            # Convertimos el diccionario a un DataFrame de una sola fila.
            df = pd.DataFrame([data])
            # Aseguramos que el timestamp se interprete correctamente como objeto datetime.
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # 2. Generación del nombre de archivo basado en el timestamp (formato YYYYMMDD_HHMMSS_XXX)
            # Utilizamos un formato limpio de caracteres especiales para el nombre del archivo.
            timestamp_dt = df['timestamp'].iloc[0]
            # Usamos %f para microsegundos y [:-3] para truncar a milisegundos y evitar nombres excesivamente largos.
            timestamp_str = timestamp_dt.strftime("%Y%m%d_%H%M%S_%f")[:-3] 
            file_name = f"metricas_{timestamp_str}.parquet"
            full_path = os.path.join(self._parquet_dir, file_name)

            # 3. Guardar el DataFrame a Parquet usando DuckDB
            # DuckDB es utilizado por su eficiencia en la escritura y lectura de Parquet.
            con = duckdb.connect()
            con.execute(f"INSTALL 'parquet'; LOAD 'parquet';")
            # Se usa una tabla temporal a partir del DataFrame de Pandas
            con.register('df', df) 
            con.execute(f"CREATE OR REPLACE TABLE metricas_temp AS SELECT * FROM df")
            # Copiar la tabla temporal al archivo Parquet
            con.execute(f"COPY metricas_temp TO '{full_path}' (FORMAT PARQUET)")
            con.close()
            
            logging.debug(f"Archivo Parquet guardado exitosamente: {full_path}")
            return True

        except Exception as e:
            logging.error(f"Error al guardar métricas a Parquet: {e}")
            return False

    def clean_old_parquet_files(self):
        """
        Elimina archivos Parquet del directorio que superen el tiempo de 
        retención configurado (generalmente 60 minutos). 
        Se basa en el timestamp codificado en el nombre del archivo.
        """
        if not self._parquet_dir:
            return

        # Calcular el punto de corte (hora actual - tiempo de retención)
        cutoff_time = datetime.now() - timedelta(minutes=self._retention_minutes)
        
        logging.info(f"Iniciando limpieza de archivos Parquet. Retención: {self._retention_minutes} minutos.")

        try:
            for filename in os.listdir(self._parquet_dir):
                if filename.endswith(".parquet") and filename.startswith("metricas_"):
                    full_path = os.path.join(self._parquet_dir, filename)
                    
                    # Extraer el timestamp del nombre del archivo (formato: YYYYMMDD_HHMMSS_XXX)
                    try:
                        # Extraer solo la parte del timestamp (desde índice 9 hasta antes de la extensión '.parquet')
                        # El slicing es [9:-8] porque 'metricas_' tiene 9 caracteres y '.parquet' tiene 8.
                        timestamp_part = filename[9:-8] 
                        # Parsear la cadena del timestamp al objeto datetime.
                        file_timestamp = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S_%f")

                        if file_timestamp < cutoff_time:
                            os.remove(full_path)
                            logging.warning(f"Archivo Parquet eliminado (antigüedad > {self._retention_minutes} min): {filename}")
                    except ValueError:
                        # Ignorar archivos con nombres que no cumplen con el formato esperado.
                        logging.warning(f"Ignorando archivo con formato de nombre inválido durante la limpieza: {filename}")
                    except Exception as e:
                        logging.error(f"Error al intentar eliminar el archivo {filename}: {e}")

        except Exception as e:
            logging.error(f"Error general durante la limpieza de archivos Parquet: {e}")

    def set_retention(self, minutes):
        """Establece el tiempo de retención en minutos."""
        try:
            self._retention_minutes = int(minutes)
            logging.info(f"Tiempo de retención de Parquet establecido a {self._retention_minutes} minutos.")
        except ValueError:
            logging.error(f"El valor de retención '{minutes}' no es un número entero válido.")

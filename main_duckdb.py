import duckdb
import pandas as pd
import logging
import os
import time

class DuckDBManager:
    """
    Clase Singleton para gestionar la persistencia de datos usando DuckDB y archivos Parquet.

    Esta clase maneja dos tipos de almacenamiento:
    1. Métricas: Archivos Parquet individuales (data_{timestamp}.parquet) en la carpeta data/metricas.
    2. Info Máquina: Un único archivo Parquet (info_maquina.parquet) que se actualiza (UPSERT).
    """
    _instance = None
    _base_dir = None
    _metrics_dir = "data/metricas"
    _machine_info_file = "data/info_maquina.parquet"
    
    # Definición de las columnas de métricas para asegurar el orden y tipo de dato
    METRICS_COLUMNS = [
        'timestamp', 'hostname', 'username', 'cpu_percent', 'cpu_freq', 
        'ram_percent', 'ram_used', 'ram_total', 'ram_free', 'disk_percent', 
        'disk_used', 'disk_total', 'disk_free', 'swap_percent', 'swap_usado', 
        'swap_total', 'red_bytes_sent', 'red_bytes_recv', 'cpu_temp_celsius', 
        'battery_percent', 'cpu_power_package', 'cpu_power_cores', 'cpu_clocks'
    ]

    # Definición de las columnas de info_maquina para asegurar el orden y tipo de dato
    MACHINE_INFO_COLUMNS = [
        'hostname', 'username', 'timestamp', 'os_name', 'placa_base', 
        'procesador_nombre', 'cores_logicos', 'cores_fisicos', 'fecha_arranque'
    ]

    def __new__(cls, base_dir=None):
        """Controla la creación de la instancia Singleton."""
        if cls._instance is None:
            cls._instance = super(DuckDBManager, cls).__new__(cls)
            if base_dir:
                cls._base_dir = base_dir
                cls._instance._ensure_directories()
        return cls._instance

    @classmethod
    def close_instance(cls):
        """Método para limpiar la instancia, útil en SvcStop."""
        cls._instance = None
        logging.info("Instancia de DuckDBManager liberada.")

    def _ensure_directories(self):
        """Asegura que los directorios necesarios existan."""
        if not self._base_dir:
            logging.error("DuckDBManager no se inicializó con un directorio base.")
            return

        full_metrics_path = os.path.join(self._base_dir, self._metrics_dir)
        full_data_path = os.path.join(self._base_dir, "data")

        try:
            os.makedirs(full_metrics_path, exist_ok=True)
            os.makedirs(full_data_path, exist_ok=True)
            logging.info(f"Directorios de Parquet asegurados: {full_metrics_path}")
        except OSError as e:
            logging.error(f"Error al crear directorios: {e}")

    def insert_metrics(self, data: dict):
        """
        Guarda las métricas en un nuevo archivo Parquet timestampado.

        :param data: Diccionario con la información de métricas.
        """
        if not self._base_dir:
            logging.error("Directorio base no configurado para guardar métricas.")
            return

        try:
            # 1. Mapeo de datos (similar a la lógica de SQLite, asegurando fallbacks)
            metric_data = {
                'timestamp': data.get('timestamp'),
                'hostname': data.get('hostname'),
                'username': data.get('username'),
                'cpu_percent': data.get('cpu_percent') or data.get('cpu_freq_current_mhz') or 0.0,
                'cpu_freq': data.get('cpu_freq_current_mhz'),
                'ram_percent': data.get('memoria_percent') or data.get('ram_load_percent') or 0.0,
                'ram_used': data.get('memoria_usada_gb') or data.get('ram_load_used_gb') or 0.0,
                'ram_total': data.get('memoria_total_gb'),
                'ram_free': data.get('memoria_libre_gb') or data.get('ram_load_free_gb') or 0.0,
                'disk_percent': data.get('disco_percent') or data.get('hdd_used_gb') or 0.0,
                'disk_used': data.get('disco_usado_gb'),
                'disk_total': data.get('disco_total_gb'),
                'disk_free': data.get('disco_libre_gb'),
                'swap_percent': data.get('swap_percent'),
                'swap_usado': data.get('swap_usado_gb'),
                'swap_total': data.get('swap_total_gb'),
                'red_bytes_sent': data.get('red_bytes_enviados'),
                'red_bytes_recv': data.get('red_bytes_recibidos'),
                'cpu_temp_celsius': data.get('cpu_temperatura_celsius'),
                'battery_percent': data.get('bateria_porcentaje'),
                'cpu_power_package': data.get('cpu_power_package_watts'),
                'cpu_power_cores': data.get('cpu_power_cores_watts'),
                'cpu_clocks': data.get('cpu_clocks_mhz')
            }

            # 2. Creación del DataFrame de Pandas
            df = pd.DataFrame([metric_data], columns=self.METRICS_COLUMNS)

            # 3. Guardar en Parquet
            timestamp = data.get('timestamp', str(time.time())).replace(':', '-').replace('.', '_')
            file_name = f"data_{timestamp}.parquet"
            full_path = os.path.join(self._base_dir, self._metrics_dir, file_name)
            
            # Utilizar compresión Snappy por ser el estándar más común y eficiente
            df.to_parquet(full_path, engine='pyarrow', compression='snappy')
            logging.debug(f"Métricas guardadas en Parquet: {full_path}")
            
        except Exception as e:
            logging.error(f"Error al guardar métricas en Parquet: {e}")

    def upsert_machine_info(self, data: dict):
        """
        Inserta o actualiza la información estática de la máquina en un único archivo Parquet.
        
        Realiza un 'UPSERT' lógico: lee el archivo, actualiza si existe la clave, 
        inserta si no, y sobrescribe el archivo Parquet.

        :param data: Diccionario con la información de la máquina.
        """
        if not self._base_dir:
            logging.error("Directorio base no configurado para UPSERT de info_maquina.")
            return

        full_path = os.path.join(self._base_dir, self._machine_info_file)
        
        try:
            # 1. Preparación de los datos
            placa_base_fabricante = data.get('placa_base_fabricante', 'Desconocido')
            placa_base_producto = data.get('placa_base_producto', 'Desconocido')
            placa_base_combined = f"{placa_base_fabricante} - {placa_base_producto}".replace("Desconocido - ", "").replace(" - Desconocido", "")
            if placa_base_combined.strip() == '':
                 placa_base_combined = 'Desconocido'

            new_info_data = {
                'hostname': data.get('hostname'),
                'username': data.get('username'),
                'timestamp': data.get('timestamp'),
                'os_name': data.get('os_name'),
                'placa_base': placa_base_combined,
                'procesador_nombre': data.get('procesador_nombre'),
                'cores_logicos': data.get('procesador_nucleos_logicos'),
                'cores_fisicos': data.get('procesador_nucleos_fisicos'),
                'fecha_arranque': data.get('os_last_boot_up_time')
            }
            
            # Crear un DataFrame temporal con la nueva información
            df_new = pd.DataFrame([new_info_data], columns=self.MACHINE_INFO_COLUMNS)
            
            # 2. Lógica UPSERT utilizando DuckDB
            # Conexión a un DuckDB in-memory
            con = duckdb.connect(database=':memory:', read_only=False)
            
            # Crear la tabla de info_maquina con la nueva información
            con.execute("CREATE OR REPLACE TABLE info_maquina AS SELECT * FROM df_new")

            if os.path.exists(full_path):
                # 2a. Leer el archivo Parquet existente
                con.execute(f"CREATE TEMP TABLE existing_info AS SELECT * FROM read_parquet('{full_path}')")
                
                # 2b. Ejecutar el UPSERT lógico: 
                # Se insertan los nuevos datos, reemplazando las filas donde haya colisiones 
                # en las claves (hostname, username). 
                # Si las claves son las mismas, se prefiere la fila más reciente (de df_new en la tabla 'info_maquina' actual)
                # Omitiremos la lógica de MERGE y usaremos la reescritura de tabla
                
                # Cargar el DF existente
                df_existing = pd.read_parquet(full_path)
                con.register('df_existing', df_existing)
                
                # Combinar y quitar duplicados, manteniendo la fila del nuevo DataFrame (df_new)
                # Se usa UNION ALL para apilar, y luego se quitan duplicados basándose en las claves primarias (hostname, username)
                # El nuevo registro se coloca al final (df_new) para que sea el preferido en la deduplicación (ORDER BY)
                
                # 2c. Ejecutar la lógica de combinación (Union y Deduplicación)
                result = con.execute("""
                    SELECT * FROM (
                        SELECT * FROM df_existing 
                        UNION ALL 
                        SELECT * FROM df_new
                    ) AS combined
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY hostname, username ORDER BY timestamp DESC) = 1
                """).fetchdf()
            else:
                # Si el archivo no existe, el resultado es simplemente el nuevo DataFrame
                result = df_new

            # 3. Guardar el DataFrame final de vuelta en el archivo Parquet (sobrescribir)
            result.to_parquet(full_path, engine='pyarrow', compression='snappy')
            con.close()
            logging.debug(f"Información de máquina UPSERT completada en Parquet: {full_path}")

        except Exception as e:
            logging.error(f"Error al realizar UPSERT en info_maquina.parquet: {e}")

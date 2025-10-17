import duckdb
import logging
import os
import sys

# Se añade una función para manejar las excepciones de importación
try:
    import duckdb
    # **CORRECCIÓN:** Verificar si DuckDBError existe y capturar el tipo de excepción para usarlo
    # Esto soluciona el error 'module 'duckdb' has no attribute 'DuckDBError''
    DUCKDB_EXCEPTION = getattr(duckdb, 'DuckDBError', Exception)
except ImportError as e:
    logging.error(f"La librería duckdb no pudo ser importada. Asegúrese de que esté instalada y empaquetada correctamente. Error: {e}")
    DUCKDB_EXCEPTION = Exception # Usar Exception como fallback si la importación falla

class DBManager:
    """
    Clase Singleton para gestionar la ruta de la base de datos DuckDB,
    implementando un mecanismo de cola para manejar bloqueos de archivos.
    
    La escritura intenta primero en la DB principal. Si falla por un bloqueo,
    la información se almacena en 'monitoreo_queue.duckdb'. Antes de cada escritura,
    se intenta migrar la cola a la DB principal si esta está disponible.
    """
    _instance = None
    _db_path = None
    _queue_db_path = None # Nueva ruta para la base de datos de cola

    def __new__(cls, db_path=None):
        """
        Controla la creación de la instancia para asegurar el patrón Singleton
        y configura las rutas de las bases de datos principal y de cola.
        """
        if cls._instance is None:
            # Creación de la única instancia
            cls._instance = super(DBManager, cls).__new__(cls)
            if db_path:
                cls._db_path = db_path
                # Lógica para determinar la ruta de la base de datos de cola
                base_dir = os.path.dirname(db_path)
                file_name = os.path.basename(db_path)
                # Reemplaza .duckdb con _queue.duckdb
                queue_file_name = file_name.replace(".duckdb", "_queue.duckdb")
                cls._queue_db_path = os.path.join(base_dir, queue_file_name)
            else:
                cls._queue_db_path = None
        return cls._instance

    def _connect_and_execute(self, db_path: str, query: str, params: tuple = None, is_write: bool = False) -> bool:
        """
        Método privado de bajo nivel para establecer una conexión transitoria, 
        ejecutar una consulta y cerrar la conexión en una ruta de DB específica.

        Se ha modificado la gestión de excepciones para ser más resiliente,
        utilizando la excepción DUCKDB_EXCEPTION (que es 'DuckDBError' o 
        'Exception' como fallback) para manejar los errores de DuckDB/Bloqueo.

        :param db_path: La ruta de la base de datos DuckDB a conectar.
        :param query: La consulta SQL a ejecutar.
        :param params: Parámetros para la consulta parametrizada.
        :param is_write: Indica si la operación es de escritura, para propósitos de logging.
        :return: True si la ejecución fue exitosa, False en caso de error de DuckDB/Bloqueo.
        """
        if not db_path:
            logging.error("Ruta de la base de datos DuckDB no configurada.")
            return False

        conn = None
        try:
            # Abrir conexión.
            conn = duckdb.connect(database=db_path)
            
            if params:
                conn.execute(query, params)
            else:
                conn.execute(query)
            
            if is_write:
                logging.debug(f"Operación de escritura exitosa en {os.path.basename(db_path)}.")
            
            return True
        except DUCKDB_EXCEPTION as e:
            # Captura errores de DuckDB (incluyendo bloqueos de archivos o errores de sintaxis)
            # logging.warning(f"Fallo de DB en {os.path.basename(db_path)}. Error: {e}. Posible bloqueo de archivo o error de consulta.")
            return False
        except Exception as e:
            logging.error(f"Error CRÍTICO inesperado al ejecutar consulta en {os.path.basename(db_path)}: {e}. Consulta: {query}")
            return False
        finally:
            if conn:
                # CERRAR LA CONEXIÓN es clave para liberar el bloqueo del archivo.
                conn.close()

    def _ensure_tables(self, db_path: str):
        """Asegura que las tablas 'metricas' e 'info_maquina' existan en la DB especificada."""
        # Nota: La lógica de creación de tablas ahora se llama con una ruta específica
        self._create_table_metricas(db_path)
        self._create_table_machine_info(db_path)

    def _create_table_metricas(self, db_path: str):
        """Crea la tabla 'metricas' si no existe."""
        query = """
            CREATE TABLE IF NOT EXISTS metricas (
                timestamp TEXT PRIMARY KEY,
                hostname TEXT,
                username TEXT,
                cpu_percent DOUBLE,
                cpu_freq DOUBLE,
                ram_percent DOUBLE,
                ram_used DOUBLE,
                ram_total DOUBLE,
                ram_free DOUBLE,
                disk_percent DOUBLE,
                disk_used DOUBLE,
                disk_total DOUBLE,
                disk_free DOUBLE,
                swap_percent DOUBLE,
                swap_usado DOUBLE,
                swap_total DOUBLE,
                red_bytes_sent BIGINT,
                red_bytes_recv BIGINT,
                cpu_temp_celsius DOUBLE,
                battery_percent DOUBLE,
                cpu_power_package DOUBLE,
                cpu_power_cores DOUBLE,
                cpu_clocks DOUBLE
            )
        """
        self._connect_and_execute(db_path, query, is_write=True)
        logging.debug(f"Tabla 'metricas' verificada/creada en {os.path.basename(db_path)}.")

    def _create_table_machine_info(self, db_path: str):
        """Crea la tabla 'info_maquina' si no existe."""
        query = """
            CREATE TABLE IF NOT EXISTS info_maquina (
                hostname TEXT NOT NULL,
                username TEXT NOT NULL,
                timestamp TEXT,
                os_name TEXT,
                placa_base TEXT,
                procesador_nombre TEXT,
                cores_logicos INTEGER,
                cores_fisicos INTEGER,
                fecha_arranque TEXT,
                PRIMARY KEY (hostname, username)
            )
        """
        self._connect_and_execute(db_path, query, is_write=True)
        logging.debug(f"Tabla 'info_maquina' verificada/creada en {os.path.basename(db_path)}.")


    def create_table(self):
        """ Punto de entrada para asegurar que las tablas principales existan."""
        self._ensure_tables(self._db_path)

    def create_machine_info_table(self):
        """ Punto de entrada para asegurar que la tabla info_maquina principal exista."""
        self._create_table_machine_info(self._db_path)


    def process_queue(self):
        """
        Intenta migrar los datos desde la base de datos de cola 
        ('monitoreo_queue.duckdb') a la base de datos principal 
        ('monitoreo.duckdb') y luego elimina la cola.
        """
        # Solo procede si el archivo de cola existe
        if not os.path.exists(self._queue_db_path):
            return

        logging.info(f"Intentando migrar datos de la cola ({os.path.basename(self._queue_db_path)}) a la base principal...")

        # **CORRECCIÓN:** Asegurar que las tablas de la DB principal existan antes de la migración
        self._ensure_tables(self._db_path)

        # Utiliza el ATTACH/INSERT de DuckDB para una migración eficiente.
        # Esto solo funciona si podemos abrir la conexión a la DB principal.
        migration_query_metrics = f"""
            ATTACH '{self._queue_db_path}' AS queue_db;
            BEGIN TRANSACTION;
            INSERT INTO metricas SELECT * FROM queue_db.metricas;
            COMMIT;
            DETACH queue_db;
        """
        
        migration_query_info = f"""
            ATTACH '{self._queue_db_path}' AS queue_db;
            BEGIN TRANSACTION;
            -- Usamos UPSERT para la tabla info_maquina
            INSERT INTO info_maquina 
            SELECT * FROM queue_db.info_maquina 
            ON CONFLICT (hostname, username) DO UPDATE SET
                timestamp = excluded.timestamp,
                os_name = excluded.os_name,
                placa_base = excluded.placa_base,
                procesador_nombre = excluded.procesador_nombre,
                cores_logicos = excluded.cores_logicos,
                cores_fisicos = excluded.cores_fisicos,
                fecha_arranque = excluded.fecha_arranque;
            COMMIT;
            DETACH queue_db;
        """
        
        # Intentar migrar métricas
        metrics_migrated = self._connect_and_execute(self._db_path, migration_query_metrics, is_write=True)
        # Intentar migrar info_maquina (solo si las métricas tuvieron éxito, o si falló, no importa, intentar de nuevo)
        info_migrated = self._connect_and_execute(self._db_path, migration_query_info, is_write=True)

        if metrics_migrated and info_migrated:
            # Si ambas migraciones tuvieron éxito, eliminar el archivo de cola
            try:
                os.remove(self._queue_db_path)
                logging.info("Migración de cola completada y archivo de cola eliminado.")
            except Exception as e:
                # Esto es un error no crítico, pero debe ser registrado
                logging.error(f"Error al intentar eliminar el archivo de cola: {e}")
        else:
            logging.warning("Fallo la migración de la cola. El archivo principal sigue bloqueado o hubo un error de DuckDB.")

    def _execute_write_operation(self, query: str, params: tuple = None, table_name: str = 'metricas'):
        """
        Lógica de escritura principal con fallback a la cola.
        
        :param query: Consulta SQL a ejecutar.
        :param params: Parámetros de la consulta.
        :param table_name: Nombre de la tabla (usado para asegurar la existencia en la cola).
        """
        # 1. Intentar vaciar la cola antes de la nueva escritura (si la DB principal está libre)
        self.process_queue()

        # 2. Intentar escribir en la base de datos principal
        main_success = self._connect_and_execute(self._db_path, query, params, is_write=True)

        if main_success:
            return True
        else:
            # 3. Fallback: Escribir en la base de datos de cola
            logging.warning(f"Fallo la escritura en {os.path.basename(self._db_path)}. Redirigiendo a {os.path.basename(self._queue_db_path)}.")
            
            # Asegurar que las tablas de cola existan antes de escribir en ella por primera vez
            # Al fallar la escritura principal, la DB de cola debe crearse/verificarse aquí.
            self._ensure_tables(self._queue_db_path)

            queue_success = self._connect_and_execute(self._queue_db_path, query, params, is_write=True)
            
            if queue_success:
                # logging.info(f"Escritura exitosa en la base de datos de cola.")
                return True
            else:
                # logging.error(f"Fallo critico al escribir en la base de datos de cola. Los datos se perdieron en este ciclo.")
                return False

    def upsert_machine_info(self, data):
        """
        Inserta o actualiza (UPSERT) la información de la máquina utilizando el 
        mecanismo de escritura con fallback.
        """
        try:
            # Lógica para combinar la Placa Base (sin cambios)
            placa_base_fabricante = data.get('placa_base_fabricante', 'Desconocido')
            placa_base_producto = data.get('placa_base_producto', 'Desconocido')
            
            if placa_base_fabricante == 'Desconocido' and placa_base_producto == 'Desconocido':
                placa_base_combined = 'Desconocido'
            else:
                placa_base_combined = f"{placa_base_fabricante} - {placa_base_producto}".replace("Desconocido - ", "").replace(" - Desconocido", "")

            # Columnas y Valores para la inserción
            values = (
                data.get('hostname'),
                data.get('username'),
                data.get('timestamp'),
                data.get('os_name'),
                placa_base_combined,
                data.get('procesador_nombre'),
                data.get('procesador_nucleos_logicos'),
                data.get('procesador_nucleos_fisicos'),
                data.get('os_last_boot_up_time')
            )
            
            # Consulta SQL con UPSERT (ON CONFLICT DO UPDATE)
            sql_query = """
                INSERT INTO info_maquina (
                    hostname, username, timestamp, os_name, placa_base,
                    procesador_nombre, cores_logicos, cores_fisicos, fecha_arranque
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (hostname, username) DO UPDATE SET
                    timestamp = excluded.timestamp,
                    os_name = excluded.os_name,
                    placa_base = excluded.placa_base,
                    procesador_nombre = excluded.procesador_nombre,
                    cores_logicos = excluded.cores_logicos,
                    cores_fisicos = excluded.cores_fisicos,
                    fecha_arranque = excluded.fecha_arranque
            """
            
            # Ejecución con la lógica de escritura y fallback
            self._execute_write_operation(sql_query, values, table_name='info_maquina')
            logging.debug(f"Información de máquina UPSERT gestionada para host: {data.get('hostname')}.")

        except Exception as e:
            logging.error(f"Error inesperado al procesar los datos de la máquina para UPSERT: {e}")

    def insert_metrics(self, data):
        """
        Inserta un nuevo registro de métricas utilizando el mecanismo de 
        escritura con fallback a la cola.
        """
        try:
            # Lógica de extracción y fallback de datos (sin cambios)
            cpu_percent = data.get('cpu_percent') or data.get('cpu_freq_current_mhz') or 0
            ram_percent = data.get('memoria_percent') or data.get('ram_load_percent') or 0
            ram_used = data.get('memoria_usada_gb') or data.get('ram_load_used_gb') or 0
            ram_free = data.get('memoria_libre_gb') or data.get('ram_load_free_gb') or 0
            disk_percent = data.get('disco_percent') or data.get('hdd_used_gb') or 0

            # Valores para la inserción
            values = (
                data.get('timestamp'),
                data.get('hostname'),
                data.get('username'),
                cpu_percent,
                data.get('cpu_freq_current_mhz'),
                ram_percent,
                ram_used,
                data.get('memoria_total_gb'),
                ram_free,
                disk_percent,
                data.get('disco_usado_gb'),
                data.get('disco_total_gb'),
                data.get('disco_libre_gb'),
                data.get('swap_percent'),
                data.get('swap_usado_gb'),
                data.get('swap_total_gb'),
                data.get('red_bytes_enviados'),
                data.get('red_bytes_recibidos'),
                data.get('cpu_temperatura_celsius'),
                data.get('bateria_porcentaje'),
                data.get('cpu_power_package_watts'),
                data.get('cpu_power_cores_watts'),
                data.get('cpu_clocks_mhz')
            )

            # Consulta SQL para la inserción
            sql_query = """
                INSERT INTO metricas (
                    timestamp, hostname, username, cpu_percent, cpu_freq,
                    ram_percent, ram_used, ram_total, ram_free, disk_percent,
                    disk_used, disk_total, disk_free, swap_percent, swap_usado,
                    swap_total, red_bytes_sent, red_bytes_recv, cpu_temp_celsius,
                    battery_percent, cpu_power_package, cpu_power_cores, cpu_clocks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Ejecución con la lógica de escritura y fallback
            self._execute_write_operation(sql_query, values, table_name='metricas')
            logging.debug("Métricas gestionadas para inserción.")

        except Exception as e:
            logging.error(f"Error inesperado al insertar métricas: {e}")

    # El método close_connection se mantiene como un stub, ya que la gestión es transitoria.
    def close_connection(self):
        logging.info("La gestión de conexión DuckDB es transitoria. No hay conexión persistente para cerrar.")

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

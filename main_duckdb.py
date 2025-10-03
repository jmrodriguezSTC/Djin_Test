import duckdb
import logging
import os
import sys

# Se añade una función para manejar las excepciones de importación
try:
    import duckdb
except ImportError as e:
    logging.error(f"La librería duckdb no pudo ser importada. Asegúrese de que esté instalada y empaquetada correctamente. Error: {e}")

class DBManager:
    """
    Clase Singleton para gestionar la ruta de la base de datos DuckDB.
    
    Se ha modificado para utilizar un patrón de conexión transitoria:
    la conexión a DuckDB se abre, la operación se ejecuta y la conexión se cierra
    inmediatamente para liberar el bloqueo del archivo, permitiendo la lectura concurrente.
    """
    _instance = None
    _db_path = None # Se mantiene solo la ruta, no la conexión activa.

    def __new__(cls, db_path=None):
        """
        Controla la creación de la instancia para asegurar el patrón Singleton.
        Solo almacena la ruta de la base de datos.
        """
        if cls._instance is None:
            # Creación de la única instancia
            cls._instance = super(DBManager, cls).__new__(cls)
            if db_path:
                cls._db_path = db_path
            # La conexión ya no se establece ni se verifica aquí, se hace por operación.
        return cls._instance

    def _execute_query(self, query: str, params: tuple = None, is_write: bool = True):
        """
        Método privado para establecer una conexión transitoria, ejecutar una consulta
        y cerrar la conexión.

        :param query: La consulta SQL a ejecutar.
        :param params: Parámetros para la consulta parametrizada.
        :param is_write: Indica si la operación es de escritura, para propósitos de logging.
        :return: El resultado de la consulta si es una lectura (None en este contexto de escritura).
        """
        if not self._db_path:
            logging.error("Ruta de la base de datos DuckDB no configurada.")
            return

        conn = None
        try:
            # Abrir conexión. DuckDB es eficiente abriendo y cerrando conexiones.
            # No se usa 'read_only=True' ya que esta conexión es para escritura.
            conn = duckdb.connect(database=self._db_path)
            
            if params:
                conn.execute(query, params)
            else:
                conn.execute(query)
            
            # Las operaciones de DuckDB en modo embedded suelen ser atómicas y no
            # requieren COMMIT explícito, pero el cierre de la conexión fuerza la
            # escritura de los cambios al disco (o al WAL).
            
            if is_write:
                logging.debug("Operación de escritura exitosa y conexión transitoria cerrada.")
            
        except duckdb.DuckDBError as e:
            logging.error(f"Error en operación de DuckDB: {e}. Consulta: {query}")
        except Exception as e:
            logging.error(f"Error inesperado al ejecutar consulta en DuckDB: {e}. Consulta: {query}")
        finally:
            if conn:
                # CERRAR LA CONEXIÓN es la clave para liberar el bloqueo del archivo.
                conn.close()

    def close_connection(self):
        """
        Mantenido por compatibilidad, pero ahora solo registra que no hay conexión persistente.
        La conexión es gestionada por el método _execute_query en cada operación.
        """
        logging.info("La gestión de conexión DuckDB es transitoria. No hay conexión persistente para cerrar.")
        # La lógica de cierre en SvcStop de main.py puede omitir la llamada a este método.

    def create_table(self):
        """
        Crea la tabla 'metricas' si no existe, utilizando una conexión transitoria.
        """
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
        self._execute_query(query, is_write=False)
        logging.debug("Tabla 'metricas' verificada/creada exitosamente en DuckDB (transitoria).")


    def create_machine_info_table(self):
        """
        Crea la tabla 'info_maquina' si no existe, utilizando una conexión transitoria.
        """
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
        self._execute_query(query, is_write=False)
        logging.debug("Tabla 'info_maquina' verificada/creada exitosamente en DuckDB (transitoria).")


    def upsert_machine_info(self, data):
        """
        Inserta o actualiza (UPSERT) la información de la máquina en la tabla 'info_maquina'
        utilizando una conexión transitoria.
        """
        # Asegurar que la tabla existe (conexión transitoria)
        self.create_machine_info_table()

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
            
            # Ejecución con conexión transitoria
            self._execute_query(sql_query, values)
            logging.debug(f"Información de máquina UPSERT completada para host: {data.get('hostname')}.")

        except Exception as e:
            logging.error(f"Error inesperado al procesar los datos de la máquina para UPSERT: {e}")


    def insert_metrics(self, data):
        """
        Inserta un nuevo registro de métricas en la tabla 'metricas' utilizando una conexión transitoria.
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
            
            # Ejecución con conexión transitoria
            self._execute_query(sql_query, values)
            logging.debug("Métricas insertadas en DuckDB.")

        except Exception as e:
            logging.error(f"Error inesperado al insertar métricas: {e}")

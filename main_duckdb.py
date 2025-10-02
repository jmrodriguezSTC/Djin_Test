import duckdb
import logging
import os
import sys

# Se añade una función para manejar las excepciones de importación
# ya que DuckDB es una librería externa que debe ser empaquetada.
try:
    import duckdb
except ImportError as e:
    logging.error(f"La librería duckdb no pudo ser importada. Asegúrese de que esté instalada y empaquetada correctamente. Error: {e}")
    # En un servicio real, esto podría requerir una acción más drástica.

class DBManager:
    """
    Clase Singleton para gestionar la conexión a la base de datos DuckDB.

    DuckDB se utiliza como un motor OLAP incrustado (embedded) que ofrece
    un rendimiento superior para el análisis (OLAP) sobre los datos recolectados,
    siendo altamente compatible con el API de Python para bases de datos (DB API 2.0).
    """
    _instance = None
    _connection = None
    _db_path = None

    def __new__(cls, db_path=None):
        """
        Controla la creación de la instancia para asegurar el patrón Singleton.
        Si la instancia no existe, se crea y se intenta conectar a la BD si se proporciona la ruta.
        """
        if cls._instance is None:
            # Creación de la única instancia
            cls._instance = super(DBManager, cls).__new__(cls)
            if db_path:
                cls._db_path = db_path
                cls._instance._connect()
        return cls._instance

    def _connect(self):
        """
        Método privado para establecer la conexión a la base de datos DuckDB.
        DuckDB creará el archivo de base de datos si no existe.
        """
        if not self._connection and self._db_path:
            try:
                # Establece la conexión. El archivo se crea si no existe.
                self._connection = duckdb.connect(database=self._db_path)
                logging.info(f"Conexión a la base de datos DuckDB en '{self._db_path}' establecida.")
                # Asegurar la existencia de las tablas
                self.create_table()
                self.create_machine_info_table()
            except duckdb.DuckDBError as e:
                logging.error(f"Error al conectar a la base de datos DuckDB: {e}")
                self._connection = None
            except Exception as e:
                 logging.error(f"Error inesperado durante la conexión a DuckDB: {e}")
                 self._connection = None

    def close_connection(self):
        """Cierra la conexión a la base de datos DuckDB."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logging.info("Conexión a la base de datos DuckDB cerrada.")

    def create_table(self):
        """
        Crea la tabla 'metricas' si no existe.
        Se utilizan tipos de datos compatibles con la mayoría de los motores SQL (TEXT, DOUBLE, BIGINT).
        """
        if not self._connection:
            logging.error("No hay conexión a la base de datos DuckDB.")
            return

        try:
            # DuckDB soporta la sintaxis estándar SQL para tipos y CREATE TABLE.
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS metricas (
                    timestamp TEXT PRIMARY KEY,
                    hostname TEXT,
                    username TEXT,
                    cpu_percent DOUBLE,
                    cpu_load_percent DOUBLE,
                    cpu_freq DOUBLE,
                    ram_percent DOUBLE,
                    ram_load_percent DOUBLE,
                    ram_used DOUBLE,
                    ram_load_used DOUBLE,
                    ram_total DOUBLE,
                    ram_free DOUBLE,
                    ram_load_free DOUBLE,
                    disco_percent DOUBLE,
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
                    cpu_clocks DOUBLE,
                    hdd_used DOUBLE
                )
            """)
            logging.debug("Tabla 'metricas' verificada/creada exitosamente en DuckDB.")
        except duckdb.DuckDBError as e:
            logging.error(f"Error al crear la tabla 'metricas' en DuckDB: {e}")

    def create_machine_info_table(self):
        """
        Crea la tabla 'info_maquina' si no existe para almacenar información
        estática de la máquina, utilizando la clave primaria compuesta
        (hostname, username) para el UPSERT.
        """
        if not self._connection:
            logging.error("No hay conexión a la base de datos DuckDB.")
            return

        try:
            self._connection.execute("""
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
            """)
            logging.debug("Tabla 'info_maquina' verificada/creada exitosamente en DuckDB.")
        except duckdb.DuckDBError as e:
            logging.error(f"Error al crear la tabla 'info_maquina' en DuckDB: {e}")


    def upsert_machine_info(self, data):
        """
        Inserta o actualiza (UPSERT) la información de la máquina en la tabla 'info_maquina'.
        Se utiliza la cláusula ON CONFLICT DO UPDATE, compatible con DuckDB.

        :param data: Diccionario con la información de la máquina.
        """
        if not self._connection:
            logging.error("No hay conexión a la base de datos DuckDB.")
            return

        # 1. Asegurar que la tabla existe.
        self.create_machine_info_table()

        try:
            # 2. Lógica para combinar la Placa Base
            placa_base_fabricante = data.get('placa_base_fabricante', 'Desconocido')
            placa_base_producto = data.get('placa_base_producto', 'Desconocido')

            if placa_base_fabricante == 'Desconocido' and placa_base_producto == 'Desconocido':
                placa_base_combined = 'Desconocido'
            else:
                placa_base_combined = f"{placa_base_fabricante} - {placa_base_producto}".replace("Desconocido - ", "").replace(" - Desconocido", "")

            # 3. Columnas y Valores para la inserción
            cols = [
                'hostname',
                'username',
                'timestamp',
                'os_name',
                'placa_base',
                'procesador_nombre',
                'cores_logicos',
                'cores_fisicos',
                'fecha_arranque'
            ]

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

            # 4. Consulta SQL con UPSERT (ON CONFLICT DO UPDATE)
            sql_query = f"""
                INSERT INTO info_maquina ({', '.join(cols)})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (hostname, username) DO UPDATE SET
                    timestamp = excluded.timestamp,
                    os_name = excluded.os_name,
                    placa_base = excluded.placa_base,
                    procesador_nombre = excluded.procesador_nombre,
                    cores_logicos = excluded.cores_logicos,
                    cores_fisicos = excluded.cores_fisicos,
                    fecha_arranque = excluded.fecha_arranque
            """

            # La función execute de DuckDB no requiere un 'cursor' explícito
            self._connection.execute(sql_query, values)
            logging.debug(f"Información de máquina UPSERT completada para host: {data.get('hostname')}, user: {data.get('username')}.")

        except duckdb.DuckDBError as e:
            logging.error(f"Error al insertar/actualizar la información de la máquina en DuckDB: {e}")
        except Exception as e:
            logging.error(f"Error inesperado al procesar los datos de la máquina para DuckDB: {e}")

    def insert_metrics(self, data):
        """
        Inserta un nuevo registro de métricas en la tabla 'metricas'.
        """
        if not self._connection:
            logging.error("No hay conexión a la base de datos DuckDB.")
            return

        try:
            # La consulta se mantiene igual, solo se utiliza el objeto de conexión de DuckDB.
            self._connection.execute("""
                INSERT INTO metricas (
                    timestamp,
                    hostname,
                    username,
                    cpu_percent,
                    cpu_load_percent,
                    cpu_freq,
                    ram_percent,
                    ram_load_percent,
                    ram_used,
                    ram_load_used,
                    ram_total,
                    ram_free,
                    ram_load_free,
                    disco_percent,
                    disk_used,
                    disk_total,
                    disk_free,
                    swap_percent,
                    swap_usado,
                    swap_total,
                    red_bytes_sent,
                    red_bytes_recv,
                    cpu_temp_celsius,
                    battery_percent,
                    cpu_power_package,
                    cpu_power_cores,
                    cpu_clocks,
                    hdd_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('timestamp'),
                data.get('hostname'),
                data.get('username'), # Confirmado que está presente en data
                data.get('cpu_percent'),
                data.get('cpu_load_percent'),
                data.get('cpu_freq_current_mhz'),
                data.get('memoria_percent'),
                data.get('ram_load_percent'),
                data.get('memoria_usada_gb'),
                data.get('ram_load_used_gb'),
                data.get('memoria_total_gb'),
                data.get('memoria_libre_gb'),
                data.get('ram_load_free_gb'),
                data.get('disco_percent'),
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
                data.get('cpu_clocks_mhz'),
                data.get('hdd_used_gb')
            ))
            logging.debug("Métricas insertadas en DuckDB.")

        except duckdb.DuckDBError as e:
            logging.error(f"Error al insertar métricas en DuckDB: {e}")

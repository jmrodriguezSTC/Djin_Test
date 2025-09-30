import sqlite3
import logging
import os

class DBManager:
    """
    Clase Singleton para gestionar la conexión a la base de datos SQLite.
    """
    _instance = None
    _connection = None
    _cursor = None
    _db_path = None

    def __new__(cls, db_path=None):
        """
        Método mágico que controla la creación de la instancia.
        """
        if cls._instance is None:
            # Si no existe una instancia, la creamos
            cls._instance = super(DBManager, cls).__new__(cls)
            if db_path:
                cls._db_path = db_path
                cls._instance._connect()
        return cls._instance

    def _connect(self):
        """Método privado para establecer la conexión."""
        if not self._connection:
            try:
                self._connection = sqlite3.connect(self._db_path)
                self._cursor = self._connection.cursor()
                logging.info(f"Conexión a la base de datos {self._db_path} establecida.")
                self.create_table()
            except sqlite3.Error as e:
                logging.error(f"Error al conectar a la base de datos: {e}")
                self._connection = None

    def close_connection(self):
        """Cierra la conexión a la base de datos."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logging.info("Conexión a la base de datos cerrada.")

    def create_table(self):
        """Crea la tabla si no existe para almacenar las métricas."""
        if not self._connection:
            logging.error("No hay conexión a la base de datos.")
            return

        try:
            self._cursor.execute('''
                CREATE TABLE IF NOT EXISTS metricas (
                    timestamp TEXT PRIMARY KEY,
                    hostname TEXT,
                    username TEXT,
                    cpu_percent REAL,
                    cpu_load_percent REAL,
                    cpu_freq REAL,
                    ram_percent REAL,
                    ram_load_percent REAL,
                    ram_used REAL,
                    ram_load_used REAL,
                    ram_total REAL,
                    ram_free REAL,
                    ram_load_free REAL,
                    disco_percent REAL,
                    disk_used REAL,
                    disk_total REAL,
                    disk_free REAL,
                    swap_percent REAL,
                    swap_usado REAL,
                    swap_total REAL,
                    red_bytes_sent INTEGER,
                    red_bytes_recv INTEGER,
                    cpu_temp_celsius REAL,
                    battery_percent REAL,
                    cpu_power_package REAL,
                    cpu_power_cores REAL,
                    cpu_clocks REAL,
                    hdd_used REAL
                )
            ''')
            self._connection.commit()
            logging.debug("Tabla 'metricas' verificada/creada exitosamente.")
        except sqlite3.Error as e:
            logging.error(f"Error al crear la tabla: {e}")

    def insert_metrics(self, data):
        """Inserta un nuevo registro de métricas en la base de datos."""
        if not self._connection:
            logging.error("No hay conexión a la base de datos.")
            return

        try:
            self._cursor.execute('''
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
            ''', (
                data.get('timestamp'),
                data.get('hostname'),
                data.get('username'),
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
            self._connection.commit()
            logging.debug("Métricas insertadas en la base de datos.")
        except sqlite3.Error as e:
            logging.error(f"Error al insertar métricas: {e}")

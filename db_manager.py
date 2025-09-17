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
                    cpu_percent REAL,
                    ram_percent REAL,
                    ram_used_gb REAL,
                    ram_total_gb REAL,
                    disk_percent REAL,
                    disk_used_gb REAL,
                    disk_total_gb REAL,
                    red_bytes_sent INTEGER,
                    red_bytes_recv INTEGER,
                    cpu_temp_celsius REAL,
                    placa_base_producto TEXT,
                    spooler_status TEXT,
                    network_card_ip TEXT,
                    battery_percent TEXT
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
                    cpu_percent,
                    ram_percent,
                    ram_used_gb,
                    ram_total_gb,
                    disk_percent,
                    disk_used_gb,
                    disk_total_gb,
                    red_bytes_sent,
                    red_bytes_recv,
                    cpu_temp_celsius,
                    placa_base_producto,
                    spooler_status,
                    network_card_ip,
                    battery_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('cpu_percent'),
                data.get('memoria_percent'),
                data.get('memoria_usada_gb'),
                data.get('memoria_total_gb'),
                data.get('disco_percent'),
                data.get('disco_usado_gb'),
                data.get('disco_total_gb'),
                data.get('red_bytes_enviados'),
                data.get('red_bytes_recibidos'),
                data.get('cpu_temperatura_celsius'),
                data.get('placa_base_producto'),
                data.get('estado_servicio_spooler'),
                data.get('tarjeta_red_ip'),
                data.get('bateria_porcentaje')
            ))
            self._connection.commit()
            logging.debug("Métricas insertadas en la base de datos.")
        except sqlite3.Error as e:
            logging.error(f"Error al insertar métricas: {e}")
import sqlite3
import os
import logging
from datetime import datetime

class DBManager:
    """
    Clase para gestionar la conexión y las operaciones de la base de datos SQLite.
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establece la conexión con la base de datos."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logging.info(f"Conexión a la base de datos {self.db_path} establecida.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error al conectar a la base de datos: {e}")
            return False

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            logging.info("Conexión a la base de datos cerrada.")

    def create_table(self):
        """Crea la tabla si no existe para almacenar las métricas."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos.")
            return

        try:
            # Creamos una tabla llamada 'metricas' con las columnas necesarias
            self.cursor.execute('''
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
            self.conn.commit()
            logging.info("Tabla 'metricas' verificada/creada exitosamente.")
        except sqlite3.Error as e:
            logging.error(f"Error al crear la tabla: {e}")

    def insert_metrics(self, data):
        """Inserta un nuevo registro de métricas en la base de datos."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos.")
            return

        try:
            self.cursor.execute('''
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
            self.conn.commit()
            logging.debug("Métricas insertadas en la base de datos.")
        except sqlite3.Error as e:
            logging.error(f"Error al insertar métricas: {e}")
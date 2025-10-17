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
                # Llama a la función existente para asegurar que la tabla 'metricas' existe
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
                    cpu_freq REAL,
                    ram_percent REAL,
                    ram_used REAL,
                    ram_total REAL,
                    ram_free REAL,
                    disk_percent REAL,
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
                    cpu_clocks REAL
                )
            ''')
            self._connection.commit()
            logging.debug("Tabla 'metricas' verificada/creada exitosamente.")
        except sqlite3.Error as e:
            logging.error(f"Error al crear la tabla: {e}")

    # --- Nueva funcionalidad para info_maquina ---

    def create_machine_info_table(self):
        """
        Crea la tabla 'info_maquina' si no existe.
        Utiliza 'hostname' y 'username' como clave primaria compuesta para el UPSERT.
        """
        if not self._connection:
            logging.error("No hay conexión a la base de datos.")
            return

        try:
            self._cursor.execute('''
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
            ''')
            self._connection.commit()
            logging.debug("Tabla 'info_maquina' verificada/creada exitosamente.")
        except sqlite3.Error as e:
            logging.error(f"Error al crear la tabla 'info_maquina': {e}")


    def upsert_machine_info(self, data):
        """
        Inserta o actualiza la información estática/semi-estática de la máquina en la tabla 'info_maquina'.
        La lógica de actualización/inserción (UPSERT) se basa en la coincidencia de 'hostname' y 'username'.
        Combina 'placa_base_fabricante' y 'placa_base_producto' en el campo 'placa_base'.

        :param data: Diccionario con la información de la máquina.
        """
        if not self._connection:
            logging.error("No hay conexión a la base de datos.")
            return

        # 1. Verificar/Crear la tabla 'info_maquina' si no existe.
        self.create_machine_info_table()

        try:
            # 2. Lógica para combinar la Placa Base
            placa_base_fabricante = data.get('placa_base_fabricante', 'Desconocido')
            placa_base_producto = data.get('placa_base_producto', 'Desconocido')
            
            # Formato: Fabricante - Producto. Se elimina el separador si ambos son 'Desconocido'.
            if placa_base_fabricante == 'Desconocido' and placa_base_producto == 'Desconocido':
                placa_base_combined = 'Desconocido'
            else:
                placa_base_combined = f"{placa_base_fabricante} - {placa_base_producto}".replace("Desconocido - ", "").replace(" - Desconocido", "")


            # Columnas a insertar/actualizar
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

            # Valores a insertar (asegúrate de que las keys de 'data' coincidan con estas)
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

            # Usamos ON CONFLICT DO UPDATE para el UPSERT
            # Si hay un conflicto en (hostname, username), actualiza las demás columnas.
            sql_query = f'''
                INSERT INTO info_maquina ({', '.join(cols)})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (hostname, username) DO UPDATE SET
                    timestamp = excluded.timestamp,
                    os_name = excluded.os_name, -- Columna 'os_name' actualizada
                    placa_base = excluded.placa_base,
                    procesador_nombre = excluded.procesador_nombre,
                    cores_logicos = excluded.cores_logicos,
                    cores_fisicos = excluded.cores_fisicos,
                    fecha_arranque = excluded.fecha_arranque
            '''

            self._cursor.execute(sql_query, values)
            self._connection.commit()
            logging.debug(f"Información de máquina UPSERT completada para host: {data.get('hostname')}, user: {data.get('username')}.")

        except sqlite3.Error as e:
            logging.error(f"Error al insertar/actualizar la información de la máquina: {e}")
        except Exception as e:
            logging.error(f"Error inesperado al procesar los datos de la máquina: {e}")

    # --- Fin de la nueva funcionalidad ---


    def insert_metrics(self, data):
        """Inserta un nuevo registro de métricas en la base de datos."""
        if not self._connection:
            logging.error("No hay conexión a la base de datos.")
            return

        try:
            # Lógica de extracción y fallback de datos (sin cambios)
            cpu_percent = data.get('cpu_percent') or data.get('cpu_freq_current_mhz') or 0
            ram_percent = data.get('memoria_percent') or data.get('ram_load_percent') or 0
            ram_used = data.get('memoria_usada_gb') or data.get('ram_load_used_gb') or 0
            ram_free = data.get('memoria_libre_gb') or data.get('ram_load_free_gb') or 0
            disk_percent = data.get('disco_percent') or data.get('hdd_used_gb') or 0

            self._cursor.execute('''
                INSERT INTO metricas (
                    timestamp,
                    hostname,
                    username,
                    cpu_percent,
                    cpu_freq,
                    ram_percent,
                    ram_used,
                    ram_total,
                    ram_free,
                    disk_percent,
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
                    cpu_clocks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
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
            ))
            self._connection.commit()
            logging.debug("Métricas insertadas en la base de datos.")
        except sqlite3.Error as e:
            logging.error(f"Error al insertar métricas: {e}")

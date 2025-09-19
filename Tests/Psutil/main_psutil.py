import psutil
import time
import os
import socket

print("--- Programa de Pruebas de la Librería psutil ---")
print("Este programa muestra la funcionalidad de psutil para monitorear recursos del sistema.")
print("Cada sección incluye una descripción de la función, su uso y los datos que devuelve.")
print("-" * 50)

# --- Información de la CPU ---
print("\n### Información de la CPU (psutil.cpu_*)")
print("Estas funciones obtienen datos sobre el uso y la configuración del procesador.")

# psutil.cpu_count(): Devuelve el número de CPUs lógicas o físicas.
try:
    print(f"\nNúmero de CPUs lógicas (cores): {psutil.cpu_count(logical=True)}")
    print(f"Número de CPUs físicas: {psutil.cpu_count(logical=False)}")
except Exception as e:
    print(f"Error al obtener el número de CPUs: {e}")

# psutil.cpu_percent(): Mide el porcentaje de uso de la CPU.
try:
    print("\nPorcentaje de uso de la CPU (durante 1 segundo):")
    # interval=1 es necesario para calcular el porcentaje de uso
    print(f"Uso total: {psutil.cpu_percent(interval=1)}%")
    print(f"Uso por core: {psutil.cpu_percent(interval=1, percpu=True)}%")
except Exception as e:
    print(f"Error al obtener el porcentaje de CPU: {e}")

# psutil.cpu_times(): Devuelve las estadísticas de tiempo de la CPU.
try:
    cpu_times = psutil.cpu_times()
    print("\nTiempos de la CPU (en segundos):")
    print(f"Tiempo de usuario: {cpu_times.user:.2f}s")
    print(f"Tiempo del sistema: {cpu_times.system:.2f}s")
    print(f"Tiempo de inactividad: {cpu_times.idle:.2f}s")
except Exception as e:
    print(f"Error al obtener los tiempos de la CPU: {e}")

# psutil.cpu_freq(): Devuelve las frecuencias de la CPU.
try:
    cpu_freq = psutil.cpu_freq()
    print("\nFrecuencias de la CPU (en Mhz):")
    print(f"Actual: {cpu_freq.current:.2f}Mhz")
    print(f"Mínimo: {cpu_freq.min:.2f}Mhz")
    print(f"Máximo: {cpu_freq.max:.2f}Mhz")
except Exception as e:
    print(f"Error al obtener la frecuencia de la CPU: {e}")

# --- Información de la Memoria ---
print("\n" + "-" * 50)
print("\n### Información de la Memoria (psutil.virtual_memory() y psutil.swap_memory())")
print("Estas funciones proveen datos detallados sobre la memoria RAM y el espacio de swap.")

# psutil.virtual_memory(): Obtiene estadísticas de la memoria virtual (RAM).
try:
    mem = psutil.virtual_memory()
    print("\nEstadísticas de la Memoria Virtual (RAM):")
    print(f"Total: {mem.total / (1024**3):.2f} GB")
    print(f"Disponible: {mem.available / (1024**3):.2f} GB")
    print(f"Usada: {mem.used / (1024**3):.2f} GB")
    print(f"Porcentaje de uso: {mem.percent}%")
except Exception as e:
    print(f"Error al obtener la memoria virtual: {e}")

# psutil.swap_memory(): Obtiene estadísticas de la memoria de intercambio (swap).
try:
    swap = psutil.swap_memory()
    print("\nEstadísticas de la Memoria de Intercambio (Swap):")
    print(f"Total: {swap.total / (1024**3):.2f} GB")
    print(f"Usada: {swap.used / (1024**3):.2f} GB")
    print(f"Porcentaje de uso: {swap.percent}%")
except Exception as e:
    print(f"Error al obtener la memoria de swap: {e}")

# --- Información de los Discos ---
print("\n" + "-" * 50)
print("\n### Información de los Discos (psutil.disk_*)")
print("Estas funciones informan sobre el uso del espacio en disco y las particiones.")

# psutil.disk_partitions(): Lista todas las particiones de disco.
try:
    print("\nParticiones de disco:")
    for part in psutil.disk_partitions():
        print(f"  - Dispositivo: {part.device}, Punto de montaje: {part.mountpoint}, Tipo de sistema de archivos: {part.fstype}")
except Exception as e:
    print(f"Error al obtener las particiones: {e}")

# psutil.disk_usage(): Muestra el uso del disco para un punto de montaje.
try:
    # Obtener el punto de montaje del directorio actual
    current_mountpoint = os.path.abspath(os.sep)
    disk_usage = psutil.disk_usage(current_mountpoint)
    print(f"\nUso del disco en '{current_mountpoint}':")
    print(f"Total: {disk_usage.total / (1024**3):.2f} GB")
    print(f"Usado: {disk_usage.used / (1024**3):.2f} GB")
    print(f"Libre: {disk_usage.free / (1024**3):.2f} GB")
    print(f"Porcentaje de uso: {disk_usage.percent}%")
except Exception as e:
    print(f"Error al obtener el uso del disco: {e}")

# --- Información de la Red ---
print("\n" + "-" * 50)
print("\n### Información de la Red (psutil.net_*)")
print("Estas funciones proporcionan estadísticas sobre la red, como bytes enviados y recibidos.")

# psutil.net_io_counters(): Obtiene estadísticas de E/S de red.
try:
    net_io = psutil.net_io_counters()
    print("\nEstadísticas de E/S de Red:")
    print(f"Bytes enviados: {net_io.bytes_sent / (1024**2):.2f} MB")
    print(f"Bytes recibidos: {net_io.bytes_recv / (1024**2):.2f} MB")
except Exception as e:
    print(f"Error al obtener las estadísticas de red: {e}")

# psutil.net_if_addrs(): Muestra las direcciones de las interfaces de red.
try:
    print("\nDirecciones de las interfaces de red:")
    for interface, addrs in psutil.net_if_addrs().items():
        print(f"  - Interfaz: {interface}")
        for addr in addrs:
            if addr.family == socket.AF_LINK:  # Dirección MAC
                print(f"      Dirección MAC: {addr.address}")
            elif addr.family == socket.AF_INET:  # IPv4
                print(f"      Dirección IPv4: {addr.address}")
            elif addr.family == socket.AF_INET6:  # IPv6
                print(f"      Dirección IPv6: {addr.address}")
            else:
                print(f"      Dirección {addr.family}: {addr.address}")
except Exception as e:
    print(f"Error al obtener las direcciones de red: {e}")

# --- Información de los Procesos ---
print("\n" + "-" * 50)
print("\n### Información de los Procesos")
print("Estas funciones listan y detallan la información de los procesos en ejecución.")

# psutil.pids(): Devuelve una lista de todos los PIDs (identificadores de proceso).
try:
    pids = psutil.pids()
    print(f"\nNúmero total de procesos en ejecución: {len(pids)}")
except Exception as e:
    print(f"Error al obtener la lista de PIDs: {e}")

# psutil.Process(): Obtiene información detallada de un proceso específico.
try:
    # Usar el PID del proceso actual del script
    current_process = psutil.Process(os.getpid())
    print(f"\nInformación del proceso actual (PID: {current_process.pid}):")
    print(f"  Nombre: {current_process.name()}")
    print(f"  Uso de memoria (RSS): {current_process.memory_info().rss / (1024**2):.2f} MB")
    print(f"  Uso de CPU: {current_process.cpu_percent(interval=1)}%")
    print(f"  Estado: {current_process.status()}")
except Exception as e:
    print(f"Error al obtener la información del proceso actual: {e}")

# psutil.process_iter(): Obtiene información detallada de un proceso específico.
procesos = []
try:
    print(f"\nLista de procesos actuales (PID y Nombre):")
    for proc in psutil.process_iter(['pid', 'name']):
        print(f"  PID: {proc.pid} | Nombre: {proc.name()}")
except Exception as e:
    print(f"Error al listar procesos: {e}")

# --- Nueva Sección de Sensores y Sistema ---
print("\n" + "-" * 50)
print("\n### Información de Sensores y Sistema (psutil.sensors_*, psutil.boot_time, psutil.users)")
print("Estas funciones proveen datos sobre la temperatura, estado de la batería, tiempo de arranque y usuarios.")

# psutil.sensors_temperatures(): Obtiene la temperatura de los sensores del sistema (si están disponibles).
try:
    temperatures = psutil.sensors_temperatures()
    if temperatures:
        print("\nTemperaturas del sistema:")
        for name, entries in temperatures.items():
            print(f"  - {name}:")
            for entry in entries:
                print(f"      Etiqueta: {entry.label}, Temperatura actual: {entry.current}°C")
    else:
        print("\nNo se encontraron datos de temperatura.")
except Exception as e:
    print(f"Error al obtener la temperatura de los sensores: {e}")

# psutil.sensors_fans(): Obtiene la velocidad de los ventiladores del sistema (si están disponibles).
try:
    fans = psutil.sensors_fans()
    if fans:
        print("\nVelocidad de los ventiladores:")
        for name, entries in fans.items():
            print(f"  - {name}:")
            for entry in entries:
                print(f"      Etiqueta: {entry.label}, Velocidad: {entry.current} RPM")
    else:
        print("\nNo se encontraron datos de ventiladores.")
except Exception as e:
    print(f"Error al obtener la velocidad de los ventiladores: {e}")

# psutil.sensors_battery(): Obtiene el estado de la batería (si está disponible).
try:
    battery = psutil.sensors_battery()
    if battery:
        print("\nEstado de la batería:")
        print(f"  Carga: {battery.percent}%")
        print(f"  Estado de energía: {'Cargando' if battery.power_plugged else 'Descargando'}")
        print(f"  Tiempo restante: {battery.secsleft // 60} minutos")
    else:
        print("\nNo se encontraron datos de batería.")
except Exception as e:
    print(f"Error al obtener los datos de la batería: {e}")

# psutil.boot_time(): Devuelve el tiempo de arranque del sistema en segundos desde la época.
try:
    boot_time_timestamp = psutil.boot_time()
    boot_time_readable = time.ctime(boot_time_timestamp)
    print(f"\nFecha y hora de arranque del sistema: {boot_time_readable}")
except Exception as e:
    print(f"Error al obtener el tiempo de arranque: {e}")

# psutil.users(): Devuelve una lista de los usuarios conectados al sistema.
try:
    users = psutil.users()
    if users:
        print("\nUsuarios actualmente conectados:")
        for user in users:
            print(f"  - Usuario: {user.name}, Terminal: {user.terminal}, Host: {user.host}, Hora de inicio: {time.ctime(user.started)}")
    else:
        print("\nNo se encontraron usuarios conectados.")
except Exception as e:
    print(f"Error al obtener los usuarios: {e}")

print("\n" + "-" * 50)
print("--- Fin del programa de pruebas de psutil. ---")
import wmi
import platform

# Crear una instancia de la clase WMI
try:
    c = wmi.WMI()
    print("--- Programa de Pruebas de la Librería wmi ---")
    print("Este programa muestra la funcionalidad de wmi para monitorear recursos del sistema Windows.")
    print("Cada sección incluye una descripción de la clase, su uso y los datos que devuelve.")
    print("-" * 50)
except wmi.x_wmi as e:
    print(f"Error al inicializar la conexión WMI: {e}")
    print("Asegúrate de estar ejecutando este script en un sistema operativo Windows.")
    exit()

# --- Información del Sistema y Procesador ---
print("\n### Información del Sistema y Procesador")
print("Usa las clases Win32_OperatingSystem y Win32_Processor para obtener detalles del sistema y la CPU.")

# Win32_OperatingSystem: Obtiene información del sistema operativo.
try:
    os_info = c.Win32_OperatingSystem()[0]
    print("\nInformación del Sistema Operativo:")
    print(f"  Nombre: {os_info.Caption}")
    print(f"  Arquitectura: {os_info.OSArchitecture}")
    print(f"  Número de serie: {os_info.SerialNumber}")
    print(f"  Último arranque: {os_info.LastBootUpTime.split('.')[0]}")
except Exception as e:
    print(f"Error al obtener la información del sistema operativo: {e}")

# Win32_Processor: Obtiene información de la CPU.
try:
    cpu_info = c.Win32_Processor()[0]
    print("\nInformación del Procesador:")
    print(f"  Nombre: {cpu_info.Name.strip()}")
    print(f"  Número de núcleos lógicos: {cpu_info.NumberOfLogicalProcessors}")
    print(f"  Número de núcleos físicos: {cpu_info.NumberOfCores}")
except Exception as e:
    print(f"Error al obtener la información del procesador: {e}")

### --- Información de la Memoria y Discos ---
print("\n" + "-" * 50)
print("\n### Información de la Memoria y Discos")
print("Se utilizan las clases Win32_PhysicalMemory y Win32_LogicalDisk.")

# Win32_PhysicalMemory: Obtiene información de los módulos de memoria RAM.
try:
    print("\nMódulos de Memoria RAM:")
    total_mem = 0
    for mem in c.Win32_PhysicalMemory():
        capacity_gb = int(mem.Capacity) / (1024**3)
        total_mem += capacity_gb
        print(f"  - Capacidad: {capacity_gb:.2f} GB, Tipo: {mem.MemoryType}, Velocidad: {mem.Speed} MHz")
    print(f"  Total de RAM instalada: {total_mem:.2f} GB")
except Exception as e:
    print(f"Error al obtener la información de la memoria RAM: {e}")

# Win32_LogicalDisk: Obtiene información de las particiones lógicas (discos).
try:
    print("\nParticiones Lógicas de Disco:")
    for disk in c.Win32_LogicalDisk(DriveType=3):  # DriveType=3 es para discos locales
        total_gb = int(disk.Size) / (1024**3)
        free_gb = int(disk.FreeSpace) / (1024**3)
        print(f"  - Unidad {disk.DeviceID} ({disk.FileSystem}):")
        print(f"      Total: {total_gb:.2f} GB")
        print(f"      Espacio libre: {free_gb:.2f} GB")
except Exception as e:
    print(f"Error al obtener la información de los discos lógicos: {e}")

### --- Información de la Red ---
print("\n" + "-" * 50)
print("\n### Información de la Red")
print("La clase Win32_NetworkAdapterConfiguration permite obtener detalles de las interfaces de red.")

# Win32_NetworkAdapterConfiguration: Obtiene la configuración de adaptadores de red.
try:
    print("\nAdaptadores de Red y Direcciones IP:")
    for adapter in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
        print(f"  - Descripción: {adapter.Description}")
        if adapter.IPAddress:
            print(f"      Dirección IPv4: {adapter.IPAddress[0]}")
        if adapter.IPSubnet:
            print(f"      Máscara de subred: {adapter.IPSubnet[0]}")
        print(f"      Dirección MAC: {adapter.MACAddress}")
except Exception as e:
    print(f"Error al obtener la configuración de red: {e}")

### --- Información de Procesos ---
print("\n" + "-" * 50)
print("\n### Información de Procesos")
print("La clase Win32_Process provee información detallada sobre los procesos en ejecución.")

# Win32_Process: Obtiene una lista de procesos y sus propiedades.
try:
    print("\nDetalles de algunos procesos en ejecución:")
    # Muestra los primeros 5 procesos
    processes = c.Win32_Process()
    print(f"\nNúmero total de procesos: {len(processes)}")
    for process in processes[:5]:
        print(f"  - PID: {process.ProcessId}, Nombre: {process.Name}, Estado: {process.ExecutionState or 'Desconocido'}")
except Exception as e:
    print(f"Error al obtener la información de los procesos: {e}")

### --- Información de Hardware Adicional ---
print("\n" + "-" * 50)
print("\n### Información de Hardware Adicional")
print("Estas clases proporcionan detalles sobre la placa base, la batería y la temperatura del sistema.")

# Win32_BaseBoard: Obtiene información sobre la placa base.
try:
    baseboard = c.Win32_BaseBoard()[0]
    print("\nInformación de la Placa Base (Motherboard):")
    print(f"  Fabricante: {baseboard.Manufacturer}")
    print(f"  Producto: {baseboard.Product}")
    print(f"  Número de serie: {baseboard.SerialNumber}")
except Exception as e:
    print(f"Error al obtener la información de la placa base: {e}")

# Win32_Battery: Obtiene el estado de la batería del sistema.
try:
    batteries = c.Win32_Battery()
    if batteries:
        print("\nEstado de la Batería:")
        battery = batteries[0] # Se asume una sola batería
        print(f"  Estado de carga: {battery.BatteryStatus}")
        print(f"  Porcentaje restante: {battery.EstimatedChargeRemaining}%")
        print(f"  Vida estimada (min): {battery.EstimatedRunTime}")
    else:
        print("\nNo se encontró una batería en este sistema.")
except Exception as e:
    print(f"Error al obtener la información de la batería: {e}")

# MSAcpi_ThermalZoneTemperature: Obtiene la temperatura de las zonas térmicas (sensores).
try:
    print("\nTemperaturas de Zonas Térmicas:")
    thermal_zones = c.MSAcpi_ThermalZoneTemperature()
    if thermal_zones:
        for zone in thermal_zones:
            # La temperatura se devuelve en Kelvin * 10. Se convierte a Celsius.
            temp_kelvin_x10 = zone.CurrentTemperature
            temp_celsius = (temp_kelvin_x10 / 10) - 273.15
            print(f"  - Nombre de la zona: {zone.Name}, Temperatura: {temp_celsius:.2f}°C")
    else:
        print("\nNo se encontraron datos de temperatura de zonas térmicas.")
except Exception as e:
    print(f"Error al obtener la temperatura de las zonas térmicas: {e}")

# --- Información de Servicios ---
print("\n" + "-" * 50)
print("\n### Información de Servicios del Sistema")
print("La clase Win32_Service() permite listar todos los servicios instalados y obtener su estado.")

# Win32_Service: Obtiene todos los servicios y su estado.
try:
    services = c.Win32_Service()
    print(f"\nNúmero total de servicios: {len(services)}")
    print("Listando los primeros 10 servicios:")
    for service in services[:10]:
        print(f"  - Nombre: {service.Name}, Estado: {service.State}, Inicio: {service.StartMode}")
except Exception as e:
    print(f"Error al obtener la información de los servicios: {e}")

print("\n" + "-" * 50)
print("--- Fin del programa de pruebas de wmi. ---")
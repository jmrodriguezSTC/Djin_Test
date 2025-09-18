import clr # Requiere el paquete 'pythonnet'
import os
import time

# Lista de tipos de hardware conocidos por OpenHardwareMonitor.
openhardwaremonitor_hwtypes = {
    'Mainboard': 'Placa Base',
    'SuperIO': 'Super I/O',
    'CPU': 'CPU',
    'RAM': 'RAM',
    'GpuNvidia': 'GPU (NVIDIA)',
    'GpuAti': 'GPU (AMD/ATI)',
    'TBalancer': 'T-Balancer',
    'Heatmaster': 'Heatmaster',
    'HDD': 'Disco Duro'
}

# Diccionario para mapear tipos de sensores a sus unidades.
sensor_units = {
    'Temperature': '°C',
    'Fan': 'RPM',
    'Load': '%',
    'Power': 'W',
    'Clock': 'MHz',
    'Voltage': 'V',
    'Data': 'GB',
    'Flow': 'L/h',
    'Control': '%',
    'Factor': ''
}

def initialize_openhardwaremonitor():
    """
    Inicializa la conexión con OpenHardwareMonitorLib.dll.
    Habilita los sensores de hardware principales.
    """
    print("Iniciando conexión con la librería OpenHardwareMonitor...")
    try:
        # Define la ruta del DLL.
        dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OpenHardwareMonitorLib.dll")
        clr.AddReference(dll_path)

        from OpenHardwareMonitor import Hardware

        # Se crea un objeto Computer que servirá de "handle".
        handle = Hardware.Computer()
        
        # Habilitar los sensores principales.
        handle.MainboardEnabled = True
        handle.CPUEnabled = True
        handle.RAMEnabled = True
        handle.GPUEnabled = True
        handle.HDDEnabled = True
        handle.Open()
        
        print("Conexión establecida. Sensores habilitados.")
        return handle
    except Exception as e:
        print(f"Error al inicializar la librería: {e}")
        print("Asegúrate de tener el archivo 'OpenHardwareMonitorLib.dll' en la misma carpeta que el script.")
        print("También, verifica que 'pythonnet' esté instalado: 'pip install pythonnet'.")
        return None

def fetch_and_print_stats(handle):
    """
    Recorre todo el hardware y sus subhardware, y extrae los datos de todos los sensores.
    """
    print("\n--- Extrayendo datos de sensores ---")
    try:
        # Itera sobre los componentes de hardware principales (CPU, GPU, RAM, etc.).
        for i in handle.Hardware:
            try:
                i.Update()  # Actualiza los datos del hardware.
                
                # Obtiene el nombre del componente de hardware para una mejor presentación.
                hw_type_name = openhardwaremonitor_hwtypes.get(i.HardwareType.ToString(), i.HardwareType.ToString())
                print(f"\n### Hardware: {hw_type_name} - {i.Name}")
                
                # Itera sobre los sensores principales del hardware.
                for sensor in i.Sensors:
                    print_sensor_info(sensor)
                
                # Itera sobre los sub-hardware (ej. núcleos de la CPU, GPUs individuales).
                for j in i.SubHardware:
                    j.Update()
                    print(f"  - Sub-Hardware: {j.Name}")
                    
                    # Itera sobre los sensores de los sub-hardware.
                    for subsensor in j.Sensors:
                        print_sensor_info(subsensor)
                        
            except Exception as e:
                print(f"Error al procesar el hardware '{i.Name}': {e}")
                
    except Exception as e:
        print(f"Error general al obtener los datos de los sensores: {e}")


def print_sensor_info(sensor):
    """
    Función auxiliar para imprimir la información de un sensor de forma ordenada.
    """
    try:
        if sensor.Value is not None:
            # Obtiene el tipo de sensor como una cadena.
            sensor_type_str = sensor.SensorType.ToString()
            # Obtiene la unidad correspondiente al tipo de sensor.
            unit = sensor_units.get(sensor_type_str, '')

            # Imprime la información del sensor.
            print(f"    - Sensor: {sensor.Name} ({sensor_type_str}) -> Valor: {sensor.Value:.2f} {unit}")
    except Exception as e:
        print(f"Error al procesar el sensor '{sensor.Name}': {e}")

if __name__ == "__main__":
    print("--- Prueba de Sensores con OpenHardwareMonitor ---")
    
    # 1. Inicializar la librería y obtener el "handle".
    HardwareHandle = initialize_openhardwaremonitor()
    
    # 2. Si la inicialización fue exitosa, obtener y mostrar los datos.
    if HardwareHandle:
        fetch_and_print_stats(HardwareHandle)
    
    print("\n" + "-" * 50)
    print("--- Fin del programa de pruebas. ---")

import logging
import os
import clr # Se necesita la biblioteca 'pythonnet'
from System import Nullable # Importación necesaria para el uso de la DLL

# Lista de tipos de hardware conocidos por OpenHardwareMonitor.
openhardwaremonitor_hwtypes = {
    'CPU': 'CPU',
    'RAM': 'RAM',
    'HDD': 'Disco Duro'
}

def initialize_openhardwaremonitor(dll_path):
    """
    Inicializa OpenHardwareMonitor llamando directamente a la DLL.

    Args:
        dll_path (str): La ruta completa al archivo OpenHardwareMonitorLib.dll.

    Returns:
        Hardware.Computer: Un objeto de control de OpenHardwareMonitor si la inicialización es exitosa,
                           de lo contrario, retorna None.
    """
    try:
        clr.AddReference(dll_path)
        from OpenHardwareMonitor import Hardware
        handle = Hardware.Computer()
        
        # Habilitar los sensores principales.
        handle.CPUEnabled = True
        handle.RAMEnabled = True
        handle.HDDEnabled = True
        
        handle.Open()
        return handle
    except Exception as e:
        logging.error(f"No se pudo inicializar OpenHardwareMonitor. Error: {e}")
        return None

def obtener_metricas_ohm(handle):
    """
    Obtiene métricas de la CPU, RAM y disco duro usando la DLL de OpenHardwareMonitor.

    Args:
        handle (Hardware.Computer): El handle de la clase Computer de OpenHardwareMonitor.

    Returns:
        dict: Un diccionario con las métricas de OHM. Retorna un diccionario vacío en caso de error.
    """
    if not handle:
        return {} # Retornar un diccionario vacío para evitar errores

    metricas_ohm = {}
    
    try:
        # Itera sobre los componentes de hardware principales (CPU, RAM, HDD, etc.).
        for hardware_item in handle.Hardware:
            hardware_item.Update()  # Actualiza los datos del hardware.
            
            # Obtiene el nombre del componente de hardware para una mejor presentación.
            hw_type_name = openhardwaremonitor_hwtypes.get(hardware_item.HardwareType.ToString(), hardware_item.HardwareType.ToString())

            if hw_type_name == 'CPU':
                metricas_ohm['cpu_name'] = hardware_item.Name
                for sensor in hardware_item.Sensors:
                    sensor_type_str = sensor.SensorType.ToString()
                    sensor_name = sensor.Name
                    
                    if sensor.Value is None:
                        continue

                    if sensor_name == 'CPU Package':
                        if sensor_type_str == 'Temperature':
                            metricas_ohm['cpu_temperatura_celsius'] = round(float(sensor.Value), 2)
                        elif sensor_type_str == 'Power':
                            metricas_ohm['cpu_power_package_watts'] = round(float(sensor.Value), 2)
                    elif sensor_name == 'CPU Total' and sensor_type_str == 'Load':
                        metricas_ohm['cpu_load_percent'] = round(float(sensor.Value), 2)
                    elif sensor_name == 'CPU Cores' and sensor_type_str == 'Power':
                        metricas_ohm['cpu_power_cores_watts'] = round(float(sensor.Value), 2)
                    elif sensor_name == 'Bus Speed' and sensor_type_str == 'Clock':
                        metricas_ohm['cpu_clocks_mhz'] = round(float(sensor.Value), 2)

            elif hw_type_name == 'RAM':
                metricas_ohm['ram_name'] = hardware_item.Name
                for sensor in hardware_item.Sensors:
                    sensor_type_str = sensor.SensorType.ToString()
                    sensor_name = sensor.Name
                    
                    if sensor.Value is None:
                        continue
                    
                    if sensor_name == 'Used Memory' and sensor_type_str == 'Data':
                        metricas_ohm['ram_load_used_gb'] = round(float(sensor.Value), 2)
                    elif sensor_name == 'Available Memory' and sensor_type_str == 'Data':
                        metricas_ohm['ram_load_free_gb'] = round(float(sensor.Value), 2)
                    elif sensor_name == 'Memory' and sensor_type_str == 'Load':
                        metricas_ohm['ram_load_percent'] = round(float(sensor.Value), 2)

            elif hw_type_name == 'Disco Duro':
                metricas_ohm['hdd_name'] = hardware_item.Name
                for sensor in hardware_item.Sensors:
                    sensor_type_str = sensor.SensorType.ToString()
                    sensor_name = sensor.Name

                    if sensor.Value is None:
                        continue

                    if sensor_name == 'Used Space' and sensor_type_str == 'Load':
                        metricas_ohm['hdd_used_gb'] = round(float(sensor.Value), 2)

    except Exception as e:
        logging.error(f"Error al obtener métricas con OpenHardwareMonitor DLL: {e}")
        return {} # Retornar un diccionario vacío para evitar fallos en el log

    return metricas_ohm

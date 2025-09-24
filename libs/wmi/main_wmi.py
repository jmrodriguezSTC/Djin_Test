import wmi
import logging
import pythoncom

def obtener_metricas_wmi():
    """
    Recopila métricas específicas de Windows usando la biblioteca wmi.

    Returns:
        dict: Un diccionario con las métricas de WMI. Retorna None en caso de error.
    """
    metricas_wmi = {}
    try:
        c = wmi.WMI()
        # Métrica: Sistema Operativo
        try:
            os_info = c.Win32_OperatingSystem()[0]
            metricas_wmi['os_name'] = os_info.Caption
            metricas_wmi['os_architecture'] = os_info.OSArchitecture
            metricas_wmi['os_serial_number'] = os_info.SerialNumber
            metricas_wmi['os_last_boot_up_time'] = os_info.LastBootUpTime.split('.')[0]
        except Exception as e:
            logging.error(f"Error al obtener métrica de sistema operativo: {e}")
            pass

        # Métrica: Placa Base
        try:
            board = c.Win32_BaseBoard()[0]
            metricas_wmi['placa_base_fabricante'] = board.Manufacturer
            metricas_wmi['placa_base_producto'] = board.Product
            metricas_wmi['placa_base_numero_serie'] = board.SerialNumber
        except Exception as e:
            logging.error(f"Error al obtener métrica de placa base: {e}")
            pass

        # Métrica: Procesador
        try:
            cpu_info = c.Win32_Processor()[0]
            metricas_wmi['procesador_nombre'] = cpu_info.Name.strip()
            metricas_wmi['procesador_nucleos_logicos'] = cpu_info.NumberOfLogicalProcessors
            metricas_wmi['procesador_nucleos_fisicos'] = cpu_info.NumberOfCores
        except Exception as e:
            logging.error(f"Error al obtener métrica de procesador: {e}")
            pass

        # Métrica: estado de la batería
        try:
            for battery in c.Win32_Battery():
                metricas_wmi['bateria_porcentaje'] = battery.EstimatedChargeRemaining
                metricas_wmi['bateria_estado'] = battery.BatteryStatus
                break
        except Exception as e:
            logging.error(f"Error al obtener métrica de batería: {e}")
            pass

    except Exception as e:
        logging.error(f"Error al obtener métricas de WMI: {e}")
        return None
    return metricas_wmi

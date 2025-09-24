import psutil
import logging

def obtener_metricas_psutil():
    """
    Recopila métricas clave del sistema usando la biblioteca psutil.
    
    Returns:
        dict: Un diccionario con las métricas del sistema. Retorna None en caso de error.
    """
    metricas = {}
    try:
        metricas['cpu_percent'] = psutil.cpu_percent(interval=1)
        metricas['cpu_core_logical'] = psutil.cpu_count(logical=True)
        metricas['cpu_core_physical'] = psutil.cpu_count(logical=False)
        metricas['cpu_freq_current_mhz'] = psutil.cpu_freq().current if psutil.cpu_freq() else None
        metricas['cpu_freq_min_mhz'] = psutil.cpu_freq().min if psutil.cpu_freq() else None
        metricas['cpu_freq_max_mhz'] = psutil.cpu_freq().max if psutil.cpu_freq() else None
        metricas['cpu_times_user'] = psutil.cpu_times().user
        metricas['cpu_times_system'] = psutil.cpu_times().system
        metricas['cpu_times_idle'] = psutil.cpu_times().idle
        memoria = psutil.virtual_memory()
        metricas['memoria_total_gb'] = round(memoria.total / (1024 ** 3), 2)
        metricas['memoria_usada_gb'] = round(memoria.used / (1024 ** 3), 2)
        metricas['memoria_libre_gb'] = round(memoria.available / (1024 ** 3), 2)
        metricas['memoria_percent'] = memoria.percent
        swap = psutil.swap_memory()
        metricas['swap_total_gb'] = round(swap.total / (1024 ** 3), 2)
        metricas['swap_usado_gb'] = round(swap.used / (1024 ** 3), 2)
        metricas['swap_percent'] = swap.percent
        disco = psutil.disk_usage('C:')
        metricas['disco_total_gb'] = round(disco.total / (1024 ** 3), 2)
        metricas['disco_usado_gb'] = round(disco.used / (1024 ** 3), 2)
        metricas['disco_libre_gb'] = round(disco.free / (1024 ** 3), 2)
        metricas['disco_percent'] = disco.percent
        red = psutil.net_io_counters()
        metricas['red_bytes_enviados'] = red.bytes_sent
        metricas['red_bytes_recibidos'] = red.bytes_recv

    except Exception as e:
        logging.error(f"Error al obtener métricas del sistema: {e}")
        return None
    return metricas

def obtener_lista_procesos():
    """
    Lista los procesos en ejecución y retorna su nombre y PID.

    Returns:
        list: Una lista de diccionarios, donde cada diccionario representa un proceso
              con su 'pid' y 'name'.
    """
    procesos = []
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            procesos.append({'pid': proc.pid, 'name': proc.name()})
    except Exception as e:
        logging.error(f"Error al listar procesos: {e}")
    return procesos

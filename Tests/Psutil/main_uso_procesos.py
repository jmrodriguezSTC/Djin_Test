# -*- coding: utf-8 -*-
import psutil
import time
import sys

def bytes_to_human_readable(bytes_value):
    """Convierte un valor en bytes a un formato legible (KB, MB, GB)."""
    if not isinstance(bytes_value, (int, float)) or bytes_value < 0:
        return 'N/A'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def listar_procesos_agrupar(sort_by='cpu', direction='desc'):
    """
    Obtiene la información de procesos, muestra una tabla completa y una tabla agrupada.
    
    Args:
        sort_by (str): Criterio para ordenar la tabla agrupada.
                       Opciones: 'name', 'cpu', 'ram', 'disk'.
        direction (str): Dirección del ordenamiento.
                         Opciones: 'asc' (ascendente) o 'desc' (descendente).
    """
    print("Recopilando información de los procesos. Por favor, espere...")

    process_data = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            p = psutil.Process(proc.info['pid'])
            
            # Recolección de datos
            data = {
                'name': p.name(),
                'pid': p.pid,
                'status': 'OK',
                'cpu_percent': p.cpu_percent(interval=0.1),
                'ram_bytes': p.memory_info().rss,
                'disk_read': p.io_counters().read_bytes,
                'disk_write': p.io_counters().write_bytes
            }
            process_data.append(data)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            data = {
                'name': proc.info.get('name', 'N/A'),
                'pid': proc.info.get('pid', 'N/A'),
                'status': 'Error'
            }
            process_data.append(data)
        except Exception:
            data = {
                'name': proc.info.get('name', 'N/A'),
                'pid': proc.info.get('pid', 'N/A'),
                'status': 'Error'
            }
            process_data.append(data)

    # --- TABLA COMPLETA CON TODOS LOS PROCESOS ---
    print("\n" + "=" * 100)
    print("TABLA COMPLETA DE PROCESOS")
    print("=" * 100)
    print(f"{'Nombre':<40} {'PID':<8} {'CPU %':<8} {'RAM':<12} {'Disco (Lect/Esc)':<25}")
    print("-" * 100)

    for p_info in process_data:
        if p_info['status'] == 'OK':
            print(f"{p_info['name'][:38]:<40} "
                  f"{p_info['pid']:<8} "
                  f"{p_info['cpu_percent']:<8.1f} "
                  f"{bytes_to_human_readable(p_info['ram_bytes']):<12} "
                  f"{bytes_to_human_readable(p_info['disk_read']):>8}/{bytes_to_human_readable(p_info['disk_write']):<12}")
        else:
            print(f"{p_info['name']:<40} {p_info['pid']:<8} Acceso denegado o no encontrado.")

    # --- TABLA AGRUPADA POR NOMBRE DE PROCESO ---
    aggregated_data = {}
    for p_info in process_data:
        name = p_info['name']
        if name not in aggregated_data:
            aggregated_data[name] = {
                'count': 0,
                'cpu_percent': 0.0,
                'ram_bytes': 0,
                'disk_read': 0,
                'disk_write': 0
            }
        
        if p_info['status'] == 'OK':
            aggregated_data[name]['count'] += 1
            aggregated_data[name]['cpu_percent'] += p_info['cpu_percent']
            aggregated_data[name]['ram_bytes'] += p_info['ram_bytes']
            aggregated_data[name]['disk_read'] += p_info['disk_read']
            aggregated_data[name]['disk_write'] += p_info['disk_write']
        else:
            aggregated_data[name]['count'] += 1

    # Lógica de ordenamiento
    sort_key = None
    
    if sort_by == 'name':
        sort_key = lambda item: item[0].lower()
    elif sort_by == 'cpu':
        sort_key = lambda item: item[1]['cpu_percent']
    elif sort_by == 'ram':
        sort_key = lambda item: item[1]['ram_bytes']
    elif sort_by == 'disk':
        sort_key = lambda item: item[1]['disk_read'] + item[1]['disk_write']
    else:
        print(f"\n¡Advertencia! Criterio de ordenamiento '{sort_by}' no válido. Usando orden por CPU.")
        sort_by = 'cpu'
        sort_key = lambda item: item[1]['cpu_percent']

    # Determinar la dirección del ordenamiento
    reverse = (direction == 'desc')
        
    sorted_items = sorted(aggregated_data.items(), key=sort_key, reverse=reverse)

    print("\n" + "=" * 100)
    print(f"TABLA AGRUPADA POR NOMBRE DE PROCESO (Criterio: {sort_by.upper()} | Dirección: {direction.upper()})")
    print("=" * 100)
    print(f"{'Nombre':<40} {'Cant.':<6} {'CPU %':<8} {'RAM':<12} {'Disco (Lect/Esc)':<25}")
    print("-" * 100)

    for name, data in sorted_items:
        print(f"{name[:38]:<40} "
              f"{data['count']:<6} "
              f"{data['cpu_percent']:<8.1f} "
              f"{bytes_to_human_readable(data['ram_bytes']):<12} "
              f"{bytes_to_human_readable(data['disk_read']):>8}/{bytes_to_human_readable(data['disk_write']):<12}")


if __name__ == "__main__":
    # Cambia los valores de estas variables para probar diferentes ordenamientos.
    # Criterio ('sort_by'): 'name', 'cpu', 'ram', 'disk'
    # Dirección ('direction'): 'asc', 'desc'
    orden_criterio = 'ram' 
    orden_direccion = 'desc'
    listar_procesos_agrupar(sort_by=orden_criterio, direction=orden_direccion)
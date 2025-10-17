import subprocess
import sys
import json
from pprint import pprint

def sort_and_limit_processes(process_list, sort_by_key="CPU (s)"):
    """
    Ordena la lista de procesos por una clave específica (descendente) y devuelve 
    los 10 procesos con los valores más altos.
    
    Args:
        process_list (list): Lista de diccionarios de procesos.
        sort_by_key (str): Clave por la cual ordenar (e.g., 'CPU (s)', 'PM (MB)').
        
    Returns:
        list: Los 10 procesos principales (o menos, si hay menos de 10).
    """
    
    # 1. Función clave para la ordenación
    # Intenta convertir el valor a un número flotante para asegurar una ordenación numérica.
    # Si la clave no existe o no es un número, usa 0 para evitar fallos.
    def get_sort_value(process):
        try:
            # Algunas claves como 'Responding' son booleanas, por lo que las manejamos 
            # de manera diferente o las excluimos de la ordenación numérica.
            if sort_by_key in ['Responding']:
                return process.get(sort_by_key, False)
            
            value = process.get(sort_by_key)
            if value is not None:
                # Intenta la conversión a float para ordenación numérica
                return float(value)
            return 0.0
        except ValueError:
            # Si el valor no es convertible a float (p.ej., una cadena de error), devuelve 0
            return 0.0
        except TypeError:
            # Maneja None o tipos inesperados
            return 0.0
    
    # 2. Ordena la lista de procesos
    # Orden descendente (reverse=True) para mostrar los valores más altos primero.
    try:
        sorted_processes = sorted(process_list, key=get_sort_value, reverse=True)
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo ordenar por la clave '{sort_by_key}'. Error: {e}")
        return process_list[:10]
        
    # 3. Limita a los 10 primeros resultados
    return sorted_processes[:10]


def get_process_stats_powershell(sort_key="CPU (s)"):
    """
    Ejecuta un comando de PowerShell para listar el consumo de recursos de los procesos,
    transforma la salida a JSON, la limpia, ordena y muestra los 10 principales.
    
    Args:
        sort_key (str): Clave para ordenar los resultados (e.g., 'CPU (s)', 'PM (MB)').
    """
    
    # Define el comando de PowerShell para obtener datos JSON
    command = """
    chcp 65001 > $null; 
    $OutputEncoding = [System.Text.Encoding]::UTF8;
    Get-Process | 
    Select-Object ProcessName, Product, Id, StartTime, Responding,
    @{Name='CPU (s)'; Expression={ [math]::Round($_.CPU, 2) }},
    @{Name='PM (MB)'; Expression={ [math]::Round($_.PM / 1MB, 2) }},
    @{Name='WS (MB)'; Expression={ [math]::Round($_.WS / 1MB, 2) }},
    @{Name='VM (MB)'; Expression={ [math]::Round($_.VM / 1MB, 2) }} | 
    ConvertTo-Json -Compress
    """
    
    try:
        # 1. Ejecuta el comando de PowerShell
        result = subprocess.run(
            [
                "powershell", 
                "-NoProfile", 
                "-Command", 
                command
            ], 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='utf-8', 
            errors='replace'
        )
        
        json_output = result.stdout.strip()
        
        if not json_output:
             print("⚠️ Advertencia: La salida de PowerShell está vacía. No se encontraron procesos.")
             return

        # 2. Carga el JSON a una lista de diccionarios
        process_list = json.loads(json_output)
        
        # 3. Lógica de Post-procesamiento (Limpieza de 'Product')
        for process in process_list:
            product_value = process.get('Product')
            process_name = process.get('ProcessName', 'N/A')
            
            if product_value is None or (isinstance(product_value, str) and not product_value.strip()):
                process['Product'] = process_name
        
        # 4. Ordena y limita los resultados
        top_processes = sort_and_limit_processes(process_list, sort_key)

        # 5. Imprime el resultado final
        print(f"🚀 Top 10 procesos ordenados por '{sort_key}' (Descendente):")
        pprint(top_processes, indent=4)
        
        # if top_processes:
        #     print("\n✅ Estructura del proceso principal (ejemplo):")
        #     pprint(top_processes[0], indent=4)
        
    except FileNotFoundError:
        print("❌ Error: PowerShell no se encuentra en el sistema.")
        sys.exit(1)
        
    except subprocess.CalledProcessError as e:
        print("❌ Error al ejecutar el comando de PowerShell.")
        print(f"Código de retorno: {e.returncode}")
        error_output = e.stderr.strip() if e.stderr else "Sin salida de error adicional."
        print(f"Salida de error: {error_output}")
        sys.exit(1)
        
    except json.JSONDecodeError as e:
        print("❌ Error de decodificación JSON.")
        print(f"Detalles: {e}")
        print(f"Salida bruta que causó el error:\n{result.stdout.strip()[:500]}...")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Puedes cambiar la clave de ordenación aquí:
    # Opciones válidas: 'CPU (s)', 'PM (MB)', 'WS (MB)', 'VM (MB)', 'StartTime', 'Id', 'ProcessName', etc.
    get_process_stats_powershell(sort_key="CPU (s)")

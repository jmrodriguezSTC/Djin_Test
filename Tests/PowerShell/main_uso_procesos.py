import subprocess
import sys
import json
from pprint import pprint

def get_process_stats_powershell():
    """
    Ejecuta un comando de PowerShell para listar el consumo de recursos de los procesos,
    formateando los valores de memoria en MB.
    
    La salida de PowerShell se fuerza a JSON usando 'ConvertTo-Json' para que 
    Python pueda transformarla fácilmente en una lista de diccionarios.
    
    SOLUCIÓN ROBUSTA A UNICODEDECODEERROR: 
    1. Se añade 'chcp 65001' al comando de PowerShell para forzar la página de códigos de la consola a UTF-8.
    2. Se añade 'errors="replace"' en Python para manejar cualquier byte no UTF-8 residual sin fallar.
    """
    
    # Define el comando de PowerShell como una cadena multilinea
    # NOTA: Se ha reemplazado 'Format-Table' por 'ConvertTo-Json -Compress'
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
        # Ejecuta el comando de PowerShell usando subprocess.run
        result = subprocess.run(
            [
                "powershell", 
                "-NoProfile", # Recomendado para iniciar PowerShell más rápido
                "-Command", 
                command
            ], 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='utf-8', 
            errors='replace' # Mitigación de fallos de decodificación
        )
        
        # La salida ahora es una cadena JSON
        json_output = result.stdout.strip()
        
        if not json_output:
             print("⚠️ Advertencia: La salida de PowerShell está vacía. No se encontraron procesos o hubo un problema de serialización.")
             return

        # Carga el JSON a una lista de diccionarios de Python
        # Cada elemento de la lista representa un proceso.
        process_list = json.loads(json_output)
        
        # --- LÓGICA DE POST-PROCESAMIENTO SOLICITADA ---
        # Si 'Product' es None o vacío, se reemplaza con 'ProcessName'.
        for process in process_list:
            product_value = process.get('Product')
            process_name = process.get('ProcessName', 'N/A')
            
            # Comprueba si el valor del producto es None O una cadena vacía/sólo espacios.
            if product_value is None or (isinstance(product_value, str) and not product_value.strip()):
                process['Product'] = process_name
        # -----------------------------------------------

        # Imprime la lista de diccionarios usando pprint para una mejor visualización estructurada
        print(f"📊 Datos de procesos transformados ({len(process_list)} procesos encontrados):")
        pprint(process_list, indent=4)
        
        if process_list:
            print("\n✅ Estructura del primer proceso (ejemplo):")
            pprint(process_list[0], indent=4)
        
    except FileNotFoundError:
        # Maneja el error si PowerShell no se encuentra
        print("❌ Error: PowerShell no se encuentra en el sistema.")
        print("Asegúrate de que PowerShell esté instalado y en tu PATH.")
        sys.exit(1)
        
    except subprocess.CalledProcessError as e:
        # Maneja los errores si el comando de PowerShell falla
        print("❌ Error al ejecutar el comando de PowerShell.")
        print(f"Código de retorno: {e.returncode}")
        error_output = e.stderr.strip() if e.stderr else "Sin salida de error adicional."
        print(f"Salida de error: {error_output}")
        sys.exit(1)
        
    except json.JSONDecodeError as e:
        # Maneja errores si la salida no es JSON válida (p.ej., si PowerShell arroja un error antes)
        print("❌ Error de decodificación JSON.")
        print(f"Detalles: {e}")
        print(f"Salida bruta que causó el error:\n{result.stdout.strip()[:500]}...")
        sys.exit(1)
        
    except Exception as e:
        # Maneja cualquier otro tipo de error inesperado
        print(f"❌ Ocurrió un error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    get_process_stats_powershell()

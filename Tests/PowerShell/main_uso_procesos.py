import subprocess
import sys

def get_process_stats_powershell():
    """
    Ejecuta un comando de PowerShell para listar el consumo de recursos de los procesos,
    formateando los valores de memoria en MB.
    """
    # Define el comando de PowerShell
    # Se usan Propiedades Calculadas para convertir los valores de memoria de bytes a MB
    # y formatear la salida de CPU.
    command = """
    Get-Process | 
    Select-Object ProcessName, Id,
    @{Name='CPU (s)'; Expression={ [math]::Round($_.CPU, 2) }},
    @{Name='PM (MB)'; Expression={ [math]::Round($_.PM / 1MB, 2) }},
    @{Name='WS (MB)'; Expression={ [math]::Round($_.WS / 1MB, 2) }},
    @{Name='VM (MB)'; Expression={ [math]::Round($_.VM / 1MB, 2) }},
    Handles | 
    Format-Table -AutoSize
    """
    
    try:
        # Ejecuta el comando de PowerShell usando subprocess.run
        result = subprocess.run(
            ["powershell", "-Command", command], 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='utf-8'
        )
        
        # Imprime la salida del comando de PowerShell
        print("📊 Estadísticas de procesos (valores de memoria en MB):")
        print(result.stdout)
        
    except FileNotFoundError:
        # Maneja el error si PowerShell no se encuentra
        print("❌ Error: PowerShell no se encuentra en el sistema.")
        print("Asegúrate de que PowerShell esté instalado y en tu PATH.")
        sys.exit(1)
        
    except subprocess.CalledProcessError as e:
        # Maneja los errores si el comando de PowerShell falla
        print("❌ Error al ejecutar el comando de PowerShell.")
        print(f"Código de retorno: {e.returncode}")
        print(f"Salida de error: {e.stderr}")
        sys.exit(1)
        
    except Exception as e:
        # Maneja cualquier otro tipo de error inesperado
        print(f"❌ Ocurrió un error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    get_process_stats_powershell()
import subprocess
import json

def get_wsus_updates():
    try:
        command = ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', 'wsus_info.ps1']
        
        # Redirecciona stderr a stdout para que se capture
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        output = result.stdout
        
        # Decodifica la salida JSON
        wsus_data = json.loads(output)
        
        # Verifica si el JSON contiene un estado de error
        if isinstance(wsus_data, dict) and wsus_data.get('status') == 'error':
            print(f"Error del script de PowerShell: {wsus_data.get('message')}")
            return None
        
        return wsus_data

    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar PowerShell: {e}")
        print(f"Salida de error: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print("Error: La salida de PowerShell no es un JSON válido.")
        return None

if __name__ == "__main__":
    updates = get_wsus_updates()
    if updates:
        print("Información de actualizaciones de WSUS no aprobadas:")
        print(json.dumps(updates, indent=4))
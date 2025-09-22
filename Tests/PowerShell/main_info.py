import subprocess
import sys
import re

def get_system_info():
    """
    Obtiene información del sistema operativo, hardware y usuario usando PowerShell.
    """
    print("Iniciando la recopilación de información del sistema con PowerShell...\n")
    
    if not sys.platform.startswith('win'):
        print("Este script está diseñado para ejecutarse en un sistema operativo Windows.")
        return

    info = {}

    # --- 1. Información del sistema operativo y la versión ---
    try:
        command = ["powershell", "-Command", "$os = Get-CimInstance Win32_OperatingSystem; $os.Caption; $os.Version"]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='cp437')
        lines = result.stdout.strip().split('\n')
        info['OS'] = lines[0]
        info['OS Version'] = lines[1]
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as e:
        info['OS'] = "No disponible"
        info['OS Version'] = "No disponible"
        print(f"Error al obtener info del SO: {e}")

    # --- 2. Información de la placa base ---
    try:
        command = ["powershell", "-Command", "Get-CimInstance Win32_BaseBoard | Format-List Manufacturer, Product"]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='cp437')
        output = result.stdout.strip()
        
        manufacturer_match = re.search(r"Manufacturer\s*:\s*(.*)", output)
        product_match = re.search(r"Product\s*:\s*(.*)", output)

        manufacturer = manufacturer_match.group(1).strip() if manufacturer_match else "Desconocido"
        product = product_match.group(1).strip() if product_match else "Desconocido"
        
        info['Motherboard'] = f"{manufacturer} - {product}"
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        info['Motherboard'] = "No disponible"
        print(f"Error al obtener info de la placa base: {e}")

    # --- 3. Información del procesador ---
    try:
        command = ["powershell", "-Command", "(Get-CimInstance Win32_Processor).Name"]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='cp437')
        info['Processor'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        info['Processor'] = "No disponible"
        print(f"Error al obtener info del procesador: {e}")

    # --- 4. Hostname de la máquina ---
    try:
        command = ["powershell", "-Command", "$env:COMPUTERNAME"]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='cp437')
        info['Hostname'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        info['Hostname'] = "No disponible"
        print(f"Error al obtener el hostname: {e}")

    # --- 5. Usuario logueado (corregido) ---
    try:
        command = ["powershell", "-Command", "(Get-CimInstance Win32_ComputerSystem).UserName"]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='cp437')
        info['Logged User'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        info['Logged User'] = "No disponible"
        print(f"Error al obtener el usuario logueado: {e}")

    # --- Mostrar la información recopilada ---
    print("\n" + "="*50)
    print("         RESUMEN DE INFORMACIÓN DEL SISTEMA")
    print("="*50)
    for key, value in info.items():
        print(f"{key:<15}: {value}")
    print("="*50)

if __name__ == "__main__":
    get_system_info()
import subprocess
import sys
import re

def ping_test_with_summary(host="8.8.8.8", count=4):
    """
    Ejecuta una cantidad específica de pings a un host y muestra un resumen detallado.

    Args:
        host (str): La dirección IP o nombre de host a la que se hará ping.
        count (int): La cantidad de pings a realizar.
    """
    print(f"Haciendo {count} pings a {host}...\n")

    if sys.platform.startswith('win'):
        command = ["ping", "-n", str(count), host]
    else:
        command = ["ping", "-c", str(count), host]

    sent = count
    received = 0
    success_rate = 0.0
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, encoding='cp437')
        output = result.stdout + result.stderr

        # print("\n" + "-"*50 + "\n")
        # print(output)
        # print("\n" + "-"*50 + "\n")

        match = None
        if sys.platform.startswith('win'):
            match = re.search(r"enviados = (\d+), recibidos = (\d+)", output)
            if not match:
                match = re.search(r"Sent = (\d+), Received = (\d+)", output)
        else:
            match = re.search(r"(\d+) packets transmitted, (\d+) received", output)

        if match:
            sent = int(match.group(1))
            received = int(match.group(2))
            
            if sent > 0:
                success_rate = (received / sent) * 100
            else:
                success_rate = 0

    except FileNotFoundError:
        print("Error: El comando 'ping' no se encontró. Asegúrate de que está en tu PATH.")
    except subprocess.TimeoutExpired:
        print(f"La operación de ping a {host} ha superado el tiempo de espera. ⏱️")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

    print("--- Resumen de la prueba de ping ---")
    print(f"Host: {host}")
    print(f"Paquetes enviados: {sent}")
    print(f"Paquetes recibidos: {received}")
    print(f"Porcentaje de éxito: {success_rate:.2f}%")
    
    if success_rate > 85:
        print("Conexión exitosa. ✅")
    elif success_rate > 0 and success_rate <= 85:
        print("Conexión inestable. ⚠️")
    else:
        print("Fallo en la conexión. ❌")

if __name__ == "__main__":
    # Prueba de un host conectado
    ping_test_with_summary(host="google.com", count=25)
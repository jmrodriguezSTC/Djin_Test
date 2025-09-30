import socket

hostname = socket.gethostname()
fqdn = socket.getfqdn() # Esto intenta obtener el nombre de dominio completo

print(f"Hostname (simple): {hostname}")
print(f"FQDN (completo): {fqdn}")
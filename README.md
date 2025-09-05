# Djin_Test

Pruebas de librerias y funcionalidades del Djin

# Comandos de Interes

Ejecutar en CMD con Administrador

- Enviroment
  Desactivar enviroment deactivate
  Activar enviroment .venv\Scripts\activate
  Crear un nuevo enviroment python -m venv .venv

- Libraries
  Instalar psutil pip install psutil
  Instalar wmi pip install wmi
  Instalar pywin32 pip install pywin32
  Instalar pyinstaller pip install pyinstaller

- Services
  Construir Ejecutable python setup.py build
  Instalar Servicio build/exe.win-amd64-3.13/PythonMonitorAgent.exe --startup auto install
  Iniciar Servicio net start "PMA_v1.0"
  Detener Servicio net stop "PMA_v1.0"

# Djin_Test

Este repositorio contiene pruebas para librerías y funcionalidades clave del proyecto **Djin**.

---

## Comandos Útiles

Ejecuta los siguientes comandos en la **línea de comandos (CMD)** con privilegios de **administrador**.

### Gestión de Entorno Virtual

- **Activar entorno:**
  ```bash
  .venv\Scripts\activate
  ```
- **Desactivar entorno:**
  ```bash
  deactivate
  ```
- **Crear nuevo entorno:**
  ```bash
  python -m venv .venv
  ```

### Requerimientos del Entorno

- **Guardar requerimientos:**

```bash
pip freeze > requirements.txt
```

### Instalación de Librerías

Puedes instalar las librerías una por una o todas juntas.

- **Instalar individualmente:**
  ```bash
  pip install psutil
  pip install wmi
  pip install pywin32
  pip install pyinstaller
  pip install cx_Freeze
  pip install pythonnet
  ```
- **Instalar todas a la vez:**
  ```bash
  pip install psutil wmi pywin32 pyinstaller cx_Freeze pythonnet
  ```
- **Instalar requerimientos:**
  ```bash
  pip install -r requirements.txt
  ```

### Creación y Gestión de Servicios

Estos comandos te ayudarán a construir y gestionar el servicio del proyecto.

- **Construir ejecutable:**
  ```bash
  python setup.py build
  ```
- **Instalar servicio:**
  ```bash
  build/Pruebas/exe.win-amd64-3.13/PythonMonitorAgent.exe --startup auto install
  ```
- **Iniciar servicio:**
  ```bash
  net start "PMA_v1.0"
  ```
- **Detener servicio:**
  ```bash
  net stop "PMA_v1.0"
  ```
- **Eliminar servicio**
  ```bash
  sc delete "my_service"
  ```

---

## Ejecución de Pruebas

Usa estos comandos para ejecutar los scripts de prueba de cada funcionalidad.

- **Pruebas con `Psutil`**
  ```bash
  python .\Tests\Psutil\main_psutil.py
  python .\Tests\Psutil\main_uso_procesos.py
  ```
- **Pruebas con `WMI`**
  ```bash
  python .\Tests\WMI\main_wmi.py
  ```
- **Pruebas con `OHM`**
  ```bash
  python .\Tests\OHM\main_dll.py
  ```
- **Pruebas con `PowerShell`**
  ```bash
  python .\Tests\PowerShell\main_uso_procesos.py
  python .\Tests\PowerShell\main_conectivity.py
  python .\Tests\PowerShell\main_info.py
  ```

# Aifred_djin

Repo que contiene el código del proceso que corre en memoria para capturar la telemetria del PC

## Gestión de Entorno Virtual

- **Crear nuevo entorno:**

  ```bash
  python -m venv .venv
  ```

- **Activar entorno:**

  ```bash
  .venv\Scripts\activate
  ```

- **Desactivar entorno:**

  ```bash
  deactivate
  ```

- **Eliminar entorno**

  Eliminar la carpeta `.venv/`

## Requerimientos y Librerias

- **Actualizar requerimientos**

  ```bash
  pip freeze > requirements.txt
  ```

- **Instalar requerimientos:**

  ```bash
  pip install -r requirements.txt
  ```

- **Instalar librerias individualmente:**

  ```bash
  pip install psutil
  ```

  ```bash
  pip install wmi
  ```

  ```bash
  pip install pywin32
  ```

  ```bash
  pip install cx_Freeze
  ```

  ```bash
  pip install pythonnet
  ```

  ```bash
  pip install pandas
  ```

  ```bash
  pip install duckdb
  ```

## Ejecución

- **Ejecución rápida**

  ```bash
  python main.py
  ```

## Gestión de Servicios

Estos comandos te ayudarán a instalar y gestionar el servicio del proyecto.

### Ejecución en root (Deprecated)

- **Instalar/actualizar servicio:**
  ```bash
  python main.py install
  ```
- **Iniciar servicio:**
  ```bash
  python main.py start
  ```
- **Detener servicio:**
  ```bash
  python main.py stop
  ```
- **Eliminar servicio**
  ```bash
  python main.py remove
  ```

### Ejecución en otro directorio

- **Construir ejecutable con dependencias:**

  ```bash
  python setup.py build
  ```

- **Instalar/actualizar servicio**

  Ir al directorio donde este el ejecutable con el cmd en administrador y ejecutar:

  - _Solo intalación/actualización:_

    ```bash
    PythonMonitorAgent.exe install
    ```

  - _Intalación/actualización con auto inicio:_

    ```bash
    PythonMonitorAgent.exe --startup auto install
    ```

  - _Iniciar servicio:_

    ```bash
    net start "name_service"
    ```

  - _Detener servicio:_

    ```bash
    net stop "name_service"
    ```

  - _Eliminar servicio_

    ```bash
    sc delete "name_service"
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

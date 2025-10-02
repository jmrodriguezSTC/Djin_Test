import duckdb
import os # Importamos 'os' para manejar rutas, ahora usado para limpieza.

def main():
    # --- 0. Configuración y Conexión ---
    
    # Nombre del archivo persistente de la base de datos
    DB_FILE = '.\Tests\DuckDB\data_test.db'
    
    # [LIMPIEZA INICIAL]
    # Si el archivo de la DB ya existe, lo eliminamos para asegurar que el script
    # se ejecute desde cero cada vez que se corre, creando una nueva tabla limpia.
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Archivo de base de datos anterior '{DB_FILE}' eliminado para un inicio limpio.")

    # [Conexión]
    # Conectamos a un archivo persistente. Si el archivo no existe, DuckDB lo crea.
    # Si el archivo existe, se conecta a la base de datos existente.
    print(f"\n--- 0. Conectando/Creando la base de datos persistente: '{DB_FILE}' ---")
    con = None # Inicializamos la conexión a None
    
    try:
        # Establecer la conexión con el archivo
        con = duckdb.connect(DB_FILE)

        # --- 1. Crear una Tabla (DDL) ---
        print("\n--- 1. Creando la tabla 'productos' ---")
        # Si la base de datos es nueva, la tabla se crea.
        # Si la base de datos ya existiera y la tabla también, esto daría un error,
        # pero la limpieza inicial lo evita en este demo.
        con.execute("""
        CREATE TABLE productos (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR NOT NULL,
            precio DOUBLE
        );
        """)
        print("Tabla 'productos' creada exitosamente con PRIMARY KEY en 'id'.")

        # --- 2. Insertar Registros (CREATE - C de CRUD) ---
        print("\n--- 2. Insertando registros iniciales ---")
        productos_a_insertar = [
            (101, 'Mouse Inalámbrico', 25.50),
            (102, 'Teclado Mecánico', 79.99),
            (103, 'Monitor 4K', 349.00)
        ]
        
        # executemany permite insertar múltiples filas de forma eficiente
        con.executemany("INSERT INTO productos VALUES (?, ?, ?)", productos_a_insertar)
        print(f"Insertados {len(productos_a_insertar)} registros.")

        # --- 3. Consultar (READ - R de CRUD) ---
        print("\n--- 3. Consulta inicial de todos los datos ---")
        # DuckDB permite usar con.sql() para ejecutar y obtener resultados directamente
        resultado_inicial = con.sql("SELECT * FROM productos ORDER BY id").fetchall()
        print(f"Columnas: {con.sql('SELECT * FROM productos').columns}")
        print(resultado_inicial)

        # --- 4. Actualizar un Registro (UPDATE - U de CRUD) ---
        # Aumentaremos el precio del Monitor (ID 103)
        print("\n--- 4. Actualizando el precio del ID 103 (Monitor 4K) a 399.99 ---")
        con.execute("UPDATE productos SET precio = 399.99 WHERE id = 103")
        
        print(f"Filas actualizadas: {con.rowcount}") # con.rowcount muestra las filas afectadas

        # Verificar la actualización
        print("Verificación después del UPDATE:")
        print(con.sql("SELECT * FROM productos WHERE id = 103").fetchall())


        # --- 5. UPSERT (Insertar o Actualizar) ---
        # DuckDB utiliza la sintaxis SQL estándar: INSERT INTO ... ON CONFLICT DO UPDATE
        
        # Caso A: Actualizar un registro existente (ID 102 - Teclado)
        print("\n--- 5a. UPSERT: Actualizando ID 102 (ON CONFLICT DO UPDATE) ---")
        con.execute("""
        INSERT INTO productos (id, nombre, precio) VALUES (102, 'Teclado Ergonómico', 85.00)
        ON CONFLICT (id) DO UPDATE SET
            nombre = EXCLUDED.nombre,
            precio = EXCLUDED.precio;
        """)
        print("Teclado 102 actualizado a 'Teclado Ergonómico'.")

        # Caso B: Insertar un registro nuevo (ID 104 - Auriculares)
        print("--- 5b. UPSERT: Insertando ID 104 (Nuevo Registro) ---")
        con.execute("""
        INSERT INTO productos (id, nombre, precio) VALUES (104, 'Auriculares Gaming', 55.00)
        ON CONFLICT (id) DO UPDATE SET
            nombre = EXCLUDED.nombre; -- Esto no se ejecuta, ya que es un INSERT
        """)
        print("Auriculares 104 insertados.")
        
        # --- 6. Eliminar un Registro (DELETE - D de CRUD) ---
        # Eliminaremos el Mouse Inalámbrico (ID 101)
        print("\n--- 6. Eliminando el producto con ID 101 (Mouse Inalámbrico) ---")
        con.execute("DELETE FROM productos WHERE id = 101")
        print(f"Filas eliminadas: {con.rowcount}")

        # --- 7. Funcionalidad Extra: Consulta Analítica y Agregación ---
        print("\n--- 7. Funcionalidad Extra: Cálculo del Precio Promedio ---")
        # Demostramos la potencia analítica de DuckDB
        promedio = con.sql("SELECT AVG(precio) FROM productos").fetchone()[0]
        print(f"Precio Promedio de los productos restantes: ${promedio:.2f}")

        # --- 8. Consulta Final ---
        print("\n--- 8. Datos finales en la tabla 'productos' ---")
        resultado_final = con.sql("SELECT * FROM productos ORDER BY id").fetchall()
        print(resultado_final)

    except duckdb.Error as e:
        print(f"\n[ERROR de DuckDB] Ocurrió un error: {e}")
    except Exception as e:
        print(f"\n[ERROR General] Ocurrió un error inesperado: {e}")
    finally:
        # [Desconexión]
        # Es fundamental asegurarse de cerrar la conexión para liberar recursos.
        if con is not None:
            con.close()
            print("\n--- Desconexión de DuckDB completada ---")


if __name__ == "__main__":
    main()

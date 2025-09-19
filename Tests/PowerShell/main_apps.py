import wmi
import matplotlib.pyplot as plt

def obtener_estado_actualizaciones():
    """
    Simula la verificación del estado de las actualizaciones de las aplicaciones.
    Devuelve un diccionario con el conteo de aplicaciones actualizadas y desactualizadas.
    """
    c = wmi.WMI()
    
    # Simulación de aplicaciones populares que están "actualizadas"
    aplicaciones_actualizadas_simuladas = [
        "Google Chrome", 
        "Mozilla Firefox", 
        "Microsoft Edge", 
        "Spotify"
    ]
    
    conteo_actualizadas = 0
    conteo_desactualizadas = 0
    
    print("Analizando aplicaciones instaladas...")
    
    for producto in c.Win32_Product():
        # Verificamos si el nombre del producto está en nuestra lista simulada de apps actualizadas
        if producto.Name in aplicaciones_actualizadas_simuladas:
            conteo_actualizadas += 1
            print(f"✅ {producto.Name} está actualizado.")
        else:
            conteo_desactualizadas += 1
            print(f"❌ {producto.Name} podría no estar actualizado.")
            
    return {"Actualizadas": conteo_actualizadas, "Desactualizadas": conteo_desactualizadas}

def visualizar_estado_actualizaciones(datos):
    """
    Crea un gráfico de barras para visualizar el estado de las actualizaciones.
    """
    etiquetas = list(datos.keys())
    valores = list(datos.values())
    
    plt.figure(figsize=(8, 6))
    barras = plt.bar(etiquetas, valores, color=['green', 'red'])
    
    plt.xlabel('Estado de la Aplicación')
    plt.ylabel('Número de Aplicaciones')
    plt.title('Estado de Actualización de las Aplicaciones Instaladas')
    
    # Añadir el número de aplicaciones encima de cada barra
    for barra in barras:
        altura = barra.get_height()
        plt.text(barra.get_x() + barra.get_width()/2.0, altura, '%d' % int(altura), ha='center', va='bottom')
        
    plt.show()

# Script principal
if __name__ == "__main__":
    try:
        # Intentamos obtener los datos
        datos_actualizaciones = obtener_estado_actualizaciones()
        
        # Si la lista no está vacía, la visualizamos
        if datos_actualizaciones["Actualizadas"] > 0 or datos_actualizaciones["Desactualizadas"] > 0:
            print("\nVisualizando el estado de las actualizaciones...")
            visualizar_estado_actualizaciones(datos_actualizaciones)
        else:
            print("No se encontraron aplicaciones para analizar.")
            
    except wmi.x_access_denied:
        print("Error: Acceso denegado. Intente ejecutar el script como Administrador.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")
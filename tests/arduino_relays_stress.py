import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def get_vector_relays(dispositivo, num_dispositivos):
    """
    dispositivo: número de dispositivo a medir (1 a N)
    num_dispositivos: cantidad total N de dispositivos
    devuelve: vector binario [R1, R2, ..., RN-1] con el estado de cada relé (0=NC, 1=NO)
    """
    # Inicializar el vector con N-1 ceros (todos los relés en posición NC)
    vector_reles = [0] * (num_dispositivos - 1)
    
    L, R = 1, num_dispositivos
    
    while L < R:
        rele = (L + R) // 2
        
        if dispositivo <= rele:
            # Rama NC (0): el relé se queda en 0 y avanzamos al subrango izquierdo
            R = rele
        else:
            # Rama NO (1): activamos el relé en la posición correspondiente (índice base 0)
            vector_reles[rele - 1] = 1
            L = rele + 1
            
    return vector_reles

def generar_mapa_cableado(num_dispositivos):
    """
    Calcula y muestra las conexiones físicas del árbol binario.
    - num_dispositivos: Cantidad N de dispositivos (1 a N)
    """
    conexiones = []

    def resolver_rango(L, R, origen_pin):
        if L == R:
            # Caso base: hoja alcanzada -> conectar con el dispositivo
            nombre_disp = chr(64 + L) if num_dispositivos <= 26 else f"D{L}"
            conexiones.append({"Origen": origen_pin, "Destino": f"Dispositivo {nombre_disp}"})
            return

        # Relé central para el rango actual
        rele_actual = (L + R) // 2
        
        # Conexión hacia el COM del relé actual
        conexiones.append({"Origen": origen_pin, "Destino": f"Relé {rele_actual} [COM]"})

        # Rama izquierda -> NC
        resolver_rango(L, rele_actual, f"Relé {rele_actual} [NC]")

        # Rama derecha -> NO
        resolver_rango(rele_actual + 1, R, f"Relé {rele_actual} [NO]")

    # Iniciar la recursión desde la SMU
    resolver_rango(1, num_dispositivos, "SMU (+)")
    
    return conexiones

def mostrar_esquema(num_dispositivos):
    conexiones = generar_mapa_cableado(num_dispositivos)
    df = pd.DataFrame(conexiones)
    
    print(f"=== TABLA PUNTO A PUNTO (N = {num_dispositivos} Dispositivos) ===")
    print(df.to_string(index=False))
    print("\n" + "="*50 + "\n")
    
    # Construcción de la Vista Agrupada por Relé
    print("=== MAPA DE TERMINALES POR RELÉ ===")
    reles_map = {f"Relé {i+1}": {"COM": "-", "NC": "-", "NO": "-"} for i in range(num_dispositivos - 1)}
    
    for c in conexiones:
        origen, destino = c["Origen"], c["Destino"]
        
        # Asignar a entradas COM
        if "COM" in destino:
            rele_nom = destino.split(" [")[0]
            reles_map[rele_nom]["COM"] = origen
            
        # Asignar a salidas NC / NO
        if "Relé" in origen:
            rele_nom, terminal = origen.split(" [")
            terminal = terminal.replace("]", "")
            reles_map[rele_nom][terminal] = destino

    df_reles = pd.DataFrame.from_dict(reles_map, orient="index")
    print(df_reles.to_string())



def plot_relay_matrix(num_dispositivos):
    # Generar la matriz donde las filas son relés y las columnas son dispositivos (o viceversa)
    # Como en el cuaderno de la foto: filas = Relés (1 a N-1), columnas = Dispositivos (A, B, C...)
    matrix = []
    for disp in range(1, num_dispositivos + 1):
        matrix.append(get_vector_relays(disp, num_dispositivos))
    
    # Transponer para que los relés sean las filas y dispositivos las columnas (igual que la foto)
    matrix = np.array(matrix).T
    
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap='Blues', vmin=0, vmax=1)
    
    # Configurar cuadrícula y etiquetas
    ax.set_xticks(np.arange(num_dispositivos))
    ax.set_yticks(np.arange(num_dispositivos - 1))
    
    # Etiquetas de dispositivos A, B, C... o 1..N
    labels_dispositivos = [chr(65 + i) for i in range(num_dispositivos)] if num_dispositivos <= 26 else [f"D{i+1}" for i in range(num_dispositivos)]
    ax.set_xticklabels(labels_dispositivos)
    ax.set_yticklabels([f"IN {i+1}" for i in range(num_dispositivos - 1)])
    
    # Añadir texto en cada celda (0 o 1)
    """
    for i in range(num_dispositivos - 1):
        for j in range(num_dispositivos):
            text = ax.text(j, i, matrix[i, j], ha="center", va="center", color="white" if matrix[i, j] == 1 else "black")
    """
            
    # Marcar bordes de cuadrícula
    ax.set_xticks(np.arange(num_dispositivos + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(num_dispositivos) - 0.5, minor=True)
    ax.grid(which="minor", color="black", linestyle='-', linewidth=1.5)
    ax.tick_params(which="minor", size=0)
    
    plt.title(f"Matriz de Activación de Relés (N={num_dispositivos} Dispositivos)")
    plt.xlabel("Dispositivos")
    plt.ylabel("Relés")
    plt.tight_layout()
    plt.show()

N = 13  # Número de dispositivos
for dispositivo in range(1, N + 1):
    print(f"Dispositivo {dispositivo}: {get_vector_relays(dispositivo, N)}")

# Ejemplo para tu caso actual (N dispositivos)
mostrar_esquema(N)

plot_relay_matrix(N)
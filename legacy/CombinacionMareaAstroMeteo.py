"""
combinar_meteo_astro.py
 
Combina la marea METEOROLÓGICA (modelo) con la marea ASTRONÓMICA (CSV externo)
para obtener el NIVEL TOTAL DEL MAR predicho, SOLO en el periodo de solape.
 
   nivel_total = eta_meteo + eta_astro
   residuo     = nivel_total - eta_astro   (= eta_meteo)
 
Salida:
  - CSV con time + meteo + astro + total + residuo (en cm y en m), inner join.
  - Figura estilo Puertos del Estado: panel superior con astro + total,
    panel inferior con el residuo + tabla horaria.
  - PNG independiente con la tabla horaria (cm).
"""
 
import os
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
 
# ================================================================
# 1. CONFIGURACIÓN
# ================================================================
 
PROJECT_ROOT = r"C:\Users\pttmc\OneDrive\Desktop\03_Python-PTT"
 
PATH_MODELO = os.path.join(PROJECT_ROOT, "data", "processed", "modelo_forecast",
                           "forecast_v2_eta_met_20260522_0929.csv")
PATH_ASTRO  = os.path.join(PROJECT_ROOT, "data", "raw", "AstronomicaPTT",
                           "astro_CAMINO_A_2026_2027_CeroREDMAR.csv")
 
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "modelo")
FIG_DIR = os.path.join(PROJECT_ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
 
PATH_SALIDA    = os.path.join(OUT_DIR, "nivel_total_meteo_astro.csv")
PATH_FIGURA    = os.path.join(FIG_DIR, "nivel_total_palma.png")
PATH_TABLA_PNG = os.path.join(FIG_DIR, "tabla_nivel_total_palma.png")
 
print("=" * 70)
print("COMBINAR METEO + ASTRO → NIVEL TOTAL (solo periodo de solape)")
print("=" * 70)
print(f"Modelo meteo:  {os.path.basename(PATH_MODELO)}")
print(f"Astronómica:   {os.path.basename(PATH_ASTRO)}")
print("=" * 70)
 
# ================================================================
# 2. CARGAR METEO (modelo)
# ================================================================
 
print("\n[1/5] Cargando marea meteorológica (modelo)...")
df_modelo = pd.read_csv(PATH_MODELO, parse_dates=['time'])
 
df_meteo = pd.DataFrame({
    'time':     df_modelo['time'],
    'meteo_m':  df_modelo['eta_met'],
    'meteo_cm': df_modelo['eta_met'] * 100,
})
print(f"   {len(df_meteo)} pasos. {df_meteo.time.iloc[0]} → {df_meteo.time.iloc[-1]}")
 
# ================================================================
# 3. CARGAR ASTRO (CSV externo, en metros)
# ================================================================
 
print("\n[2/5] Cargando marea astronómica externa...")
df_astro_raw = pd.read_csv(PATH_ASTRO)
 
col_time = df_astro_raw.columns[0]
col_val  = df_astro_raw.columns[1]
 
df_astro = pd.DataFrame({
    'time':     pd.to_datetime(df_astro_raw[col_time], format='%d-%b-%Y %H:%M:%S'),
    'astro_m':  df_astro_raw[col_val],
    'astro_cm': df_astro_raw[col_val] * 100,
})
print(f"   {len(df_astro)} pasos. {df_astro.time.iloc[0]} → {df_astro.time.iloc[-1]}")
 
# ================================================================
# 4. UNIR (INNER JOIN) Y CALCULAR NIVEL TOTAL
# ================================================================
 
print("\n[3/5] Uniendo series (inner join: solo periodo de solape)...")
df = df_meteo.merge(df_astro, on='time', how='inner').sort_values('time').reset_index(drop=True)
 
if len(df) == 0:
    raise RuntimeError("No hay solape temporal entre las dos series. Revisa las fechas.")
 
# Nivel total y residuo
df['total_m']    = df['meteo_m']  + df['astro_m']
df['total_cm']   = df['meteo_cm'] + df['astro_cm']
df['residuo_m']  = df['total_m']  - df['astro_m']   # = meteo_m
df['residuo_cm'] = df['total_cm'] - df['astro_cm']  # = meteo_cm
 
# Reordenar columnas
df = df[['time',
         'meteo_cm', 'astro_cm', 'total_cm', 'residuo_cm',
         'meteo_m',  'astro_m',  'total_m',  'residuo_m']]
 
print(f"   Periodo de solape: {df.time.iloc[0]} → {df.time.iloc[-1]}")
print(f"   Filas resultantes: {len(df)}")
 
# Guardar CSV
df.to_csv(PATH_SALIDA, index=False, float_format="%.4f")
print(f"\n[OK] CSV guardado: {PATH_SALIDA}")
 
# ================================================================
# 5. CONSTRUIR TABLA HORARIA (cm)
# ================================================================
 
# Preparar las celdas de la tabla horaria. Para que quepa con muchas filas,
# la repartimos en varios "bloques" (columnas en paralelo) dentro de la
# misma tabla de matplotlib.
def construir_tabla_multibloque(df_in, n_bloques=None, filas_por_bloque=None):
    """
    Devuelve (cell_text, col_labels) listos para ax.table().
    Cada 'bloque' contiene las columnas: Fecha | Total | Astro | Residuo (cm).
    Los bloques se colocan uno al lado del otro.
    """
    n = len(df_in)
    if filas_por_bloque is None:
        # Heurística: bloques de ~30 filas
        filas_por_bloque = 30 if n > 30 else n
    if n_bloques is None:
        n_bloques = math.ceil(n / filas_por_bloque)
        filas_por_bloque = math.ceil(n / n_bloques)
 
    # Construir lista de columnas para cada bloque
    bloques = []
    for b in range(n_bloques):
        ini = b * filas_por_bloque
        fin = min(ini + filas_por_bloque, n)
        sub = df_in.iloc[ini:fin]
        col_fecha   = [t.strftime('%d-%m %Hh') for t in sub['time']]
        col_total   = [f"{v:.1f}" for v in sub['total_cm']]
        col_astro   = [f"{v:.1f}" for v in sub['astro_cm']]
        col_residuo = [f"{v:.1f}" for v in sub['residuo_cm']]
        bloques.append([col_fecha, col_total, col_astro, col_residuo])
 
    # Igualar longitudes rellenando con celdas vacías
    max_filas = max(len(bl[0]) for bl in bloques)
    for bl in bloques:
        faltan = max_filas - len(bl[0])
        if faltan > 0:
            for c in range(4):
                bl[c] = bl[c] + [""] * faltan
 
    # Cabeceras
    col_labels = []
    for _ in range(n_bloques):
        col_labels += ["Fecha (GMT)", "Total\n(cm)", "Astro\n(cm)", "Residuo\n(cm)"]
 
    # Texto de celdas: lista de filas (cada fila tiene 4*n_bloques celdas)
    cell_text = []
    for r in range(max_filas):
        fila = []
        for bl in bloques:
            fila += [bl[0][r], bl[1][r], bl[2][r], bl[3][r]]
        cell_text.append(fila)
 
    return cell_text, col_labels, n_bloques
 
 
def dibujar_tabla(ax, cell_text, col_labels, n_bloques, fontsize=8, loc='center'):
    ax.axis('off')
    tabla = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        cellLoc='center',
        loc=loc,
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(fontsize)
    tabla.scale(1, 1.25)
 
    # Estilo: cabecera azul, columnas de "Fecha" en gris suave,
    # separador visible entre bloques
    n_cols = 4 * n_bloques
    n_filas = len(cell_text)
    for (row, col), celda in tabla.get_celld().items():
        celda.set_edgecolor('#BDC3C7')
        if row == 0:
            celda.set_facecolor('#34495E')
            celda.set_text_props(color='white', weight='bold')
        else:
            # Filas alternas
            if row % 2 == 0:
                celda.set_facecolor('#F4F6F7')
            # Columna de fecha (la primera de cada bloque)
            if col % 4 == 0:
                celda.set_text_props(weight='bold')
                if row != 0:
                    celda.set_facecolor('#EAEDED')
        # Línea vertical más gruesa entre bloques
        if col % 4 == 0 and col != 0:
            celda.set_linewidth(1.8)
 
 
# ================================================================
# 6. FIGURA PRINCIPAL: gráfica + tabla debajo
# ================================================================
 
print("\n[4/5] Generando figura principal (gráfica + tabla)...")
 
cell_text, col_labels, n_bloques = construir_tabla_multibloque(df)
n_filas_tabla = len(cell_text)
 
# Altura adaptada al número de filas de la tabla
alto_tabla = max(2.5, 0.22 * n_filas_tabla)
alto_total = 6 + alto_tabla
 
fig = plt.figure(figsize=(15, alto_total + 2))
gs = fig.add_gridspec(
    3, 1,
    height_ratios=[3, 1, alto_tabla / 1.2],
    hspace=0.9
)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1], sharex=ax1)
ax3 = fig.add_subplot(gs[2])
 
# --- Panel superior: nivel total + marea astronómica ---
ax1.plot(df.time, df.total_m,  color='#C0392B', lw=1.4, marker='o', ms=3,
         label='Nivel total (HAMSOM + Astro)')
ax1.plot(df.time, df.astro_m,  color='#E67E22', lw=1.4, marker='o', ms=3,
         label='Marea Astronómica')
ax1.axhline(0, color='gray', lw=0.5, alpha=0.6)
ax1.set_ylabel('Nivel / Marea (m)', fontsize=10)
ax1.set_title(
    f'Nivel del mar en Bahía de Palma   |   '
    f'{df.time.iloc[0]:%d-%m-%Y %H:%M} → {df.time.iloc[-1]:%d-%m-%Y %H:%M} (GMT)',
    fontsize=11
)
ax1.legend(loc='upper right', framealpha=0.9, fontsize=9)
ax1.grid(alpha=0.3)
 
# --- Panel medio: residuo ---
ax2.plot(df.time, df.residuo_m, color='#C0392B', lw=1.2, marker='o', ms=2.5)
ax2.fill_between(df.time, 0, df.residuo_m, color='#C0392B', alpha=0.15)
ax2.axhline(0, color='gray', lw=0.5, alpha=0.6)
ax2.set_ylabel('Residuo (m)', fontsize=10)
ax2.set_xlabel('Tiempo (GMT)', fontsize=10)
ax2.set_title('Residuo (nivel - marea astronómica)', fontsize=10, loc='left')
ax2.grid(alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%y %Hh'))
ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
 
# --- Panel inferior: tabla horaria ---
dibujar_tabla(ax3, cell_text, col_labels, n_bloques, fontsize=7.5, loc='upper center')
ax3.set_title('Tabla horaria de niveles (cm)', fontsize=11, weight='bold',
              loc='left', pad=8)
 
# Rotar etiquetas del eje de tiempos del residuo
for label in ax2.get_xticklabels():
    label.set_rotation(30)
    label.set_horizontalalignment('right')
 
plt.savefig(PATH_FIGURA, dpi=130, bbox_inches='tight')
plt.show()
print(f"[OK] Figura guardada:  {PATH_FIGURA}")
 
# ================================================================
# 7. PNG INDEPENDIENTE DE LA TABLA
# ================================================================
 
print("\n[5/5] Generando PNG independiente con la tabla...")
 
# Para el PNG suelto, le damos un poco más de margen
fig_t, ax_t = plt.subplots(figsize=(14, max(3, 0.28 * n_filas_tabla + 1.5)))
ax_t.set_title(
    f'Nivel del mar en Bahía de Palma — Tabla horaria (cm, Cero REDMAR)\n'
    f'{df.time.iloc[0]:%d-%m-%Y %H:%M} → {df.time.iloc[-1]:%d-%m-%Y %H:%M} (GMT)',
    fontsize=11, weight='bold', pad=15
)
dibujar_tabla(ax_t, cell_text, col_labels, n_bloques, fontsize=8)
plt.tight_layout()
plt.savefig(PATH_TABLA_PNG, dpi=150, bbox_inches='tight')
plt.show()
print(f"[OK] Tabla guardada:   {PATH_TABLA_PNG}")
 
print("=" * 70)
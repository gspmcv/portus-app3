"""
05_modelo_marea_meteo_v2.py

Versión v2 del modelo de marea meteorológica con dos mejoras:
  1. Factor IB no ideal (k_IB = 0.95) para Mediterráneo balear.
  2. Término de persistencia (alpha = 0.3) para añadir memoria al sistema.

  η_met(t) = α · η_met(t-1) + (1-α) · [k_IB · η_IB(t) + η_viento(t)]
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============ Configuración ============
PROJECT_ROOT = r"C:\Users\pttmc\OneDrive\Desktop\03_Python-PTT"
CSV_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "CSV_por_punto")
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "modelo")
FIG_DIR = os.path.join(PROJECT_ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# Punto del modelo
PUNTO_LAT = 39.25
PUNTO_LON = 2.50
csv_in = os.path.join(CSV_DIR, f"ERA5_lat{int(PUNTO_LAT*100):04d}_lon{int(PUNTO_LON*100):04d}.csv")

# ============ Coeficientes ============
A_U   = 0    # s²/m, viento E-O (literatura)
A_V   = 3.5e-4    # s²/m, viento N-S (literatura)
K_IB  = 0.93      # factor IB no ideal (Marcos et al. 2009 para Mediterráneo)
ALPHA = 0.9       # peso de persistencia (memoria del mar)

print("=" * 70)
print("MODELO v2 - Bahía de Palma (con factor IB no ideal y persistencia)")
print("=" * 70)
print(f"Punto:    {PUNTO_LAT}°N, {PUNTO_LON}°E")
print(f"Coefs:    a_u={A_U:.2e}, a_v={A_V:.2e}")
print(f"          k_IB={K_IB}, alpha={ALPHA}")
print("=" * 70)

# ============ Cargar datos ============
df = pd.read_csv(csv_in, parse_dates=['time'])
print(f"\n[1/4] {len(df)} pasos horarios cargados.")

# ============ Componentes ============
print("[2/4] Calculando componentes...")
# η_IB ya está en el CSV pero la recalculamos con k_IB
P_ref = df['msl_hPa'].mean()
df['eta_IB']   = -0.00995 * K_IB * (df['msl_hPa'] - P_ref)
df['eta_wind'] = A_U * df.u10 * np.abs(df.u10) + A_V * df.v10 * np.abs(df.v10)

# Suma instantánea (sin persistencia)
df['eta_inst'] = df['eta_IB'] + df['eta_wind']

# ============ Aplicar persistencia ============
print("[3/4] Aplicando filtro de persistencia...")
eta_met = np.zeros(len(df))
eta_met[0] = df['eta_inst'].iloc[0]   # condición inicial
for i in range(1, len(df)):
    eta_met[i] = ALPHA * eta_met[i-1] + (1 - ALPHA) * df['eta_inst'].iloc[i]
df['eta_met'] = eta_met

# Versiones en cm
df['eta_IB_cm']   = df['eta_IB']   * 100
df['eta_wind_cm'] = df['eta_wind'] * 100
df['eta_inst_cm'] = df['eta_inst'] * 100
df['eta_met_cm']  = df['eta_met']  * 100

# ============ Estadísticas ============
print("\n[4/4] Estadísticas:")
print()
print(f"{'Componente':<20}{'Mín (cm)':>12}{'Máx (cm)':>12}{'Std':>10}")
print("-" * 60)
for comp, label in [('eta_IB_cm', 'η_IB (×0.95)'),
                     ('eta_wind_cm', 'η_viento'),
                     ('eta_inst_cm', 'η_met instantánea'),
                     ('eta_met_cm', 'η_met FINAL (v2)')]:
    print(f"{label:<20}{df[comp].min():>12.2f}{df[comp].max():>12.2f}{df[comp].std():>10.2f}")

# ============ Comparación con día 2024-02-10 ============
print("\n" + "=" * 70)
print("COMPARACIÓN CON PORTUS — 2024-02-10")
print("=" * 70)

mask = (df.time >= '2024-02-10') & (df.time < '2024-02-11')
df_dia = df[mask].copy()

# Datos manuales de Portus para ese día
portus_horas = list(range(24))
portus_valores = [22.9, 23.0, 23.0, 24.2, 25.2, 25.1, 24.4, 25.1, 25.3, 23.4,
                  21.9, 21.2, 19.9, 19.0, 18.9, 18.4, 16.5, 15.3, 15.9, 16.2,
                  15.2, 15.4, 16.0, 14.2]

print(f"\n{'Hora':<6}{'Portus (cm)':>14}{'Modelo v1 (cm)':>16}{'Modelo v2 (cm)':>16}{'Δ v2-Portus':>14}")
print("-" * 70)
for i, h in enumerate(portus_horas):
    fila = df_dia.iloc[i]
    v1 = fila['eta_inst_cm']   # versión sin persistencia (~v1)
    v2 = fila['eta_met_cm']    # versión final con persistencia
    p  = portus_valores[i]
    delta = v2 - p
    print(f"{h:02d}:00 {p:14.1f}{v1:16.1f}{v2:16.1f}{delta:+14.1f}")

# Métrica de diferencia
diff_v2 = np.array([df_dia.iloc[i]['eta_met_cm'] - portus_valores[i] for i in range(24)])
diff_v1 = np.array([df_dia.iloc[i]['eta_inst_cm'] - portus_valores[i] for i in range(24)])
print(f"\nSesgo medio v1 (sin mejoras):  {diff_v1.mean():+.2f} cm")
print(f"Sesgo medio v2 (con mejoras):  {diff_v2.mean():+.2f} cm")
print(f"RMSE v1: {np.sqrt(np.mean(diff_v1**2)):.2f} cm")
print(f"RMSE v2: {np.sqrt(np.mean(diff_v2**2)):.2f} cm")

# ============ Guardar CSV ============
out_csv = os.path.join(OUT_DIR, "modelo_v2_eta_metParaGon.csv")
df_out = df[['time', 'msl_hPa', 'u10', 'v10', 'wind_speed',
             'eta_IB', 'eta_wind', 'eta_inst', 'eta_met']]
df_out.to_csv(out_csv, index=False, float_format="%.4f")
print(f"\n[OK] CSV guardado: {out_csv}")

# ============ Figura comparación ============
print("\nGenerando figura comparativa...")
fig, ax = plt.subplots(figsize=(14, 6))

ax.plot(df_dia.time, df_dia.eta_inst_cm, 'b-', lw=1.5, label='Modelo v1 (sin mejoras)', alpha=0.7)
ax.plot(df_dia.time, df_dia.eta_met_cm,  'r-', lw=2.0, label='Modelo v2 (k_IB=0.95, persistencia)')
ax.plot(df_dia.time, portus_valores,     'k.-', lw=2.0, ms=8, label='Portus (observado)')

ax.set_ylabel('Marea meteorológica (cm)')
ax.set_xlabel('Hora del 2024-02-10')
ax.set_title('Comparación modelo vs Portus — 2024-02-10')
ax.legend()
ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

plt.tight_layout()
fig_path = os.path.join(FIG_DIR, "modelo_v2_comparacion_PortusParaGon.png")
plt.savefig(fig_path, dpi=120, bbox_inches='tight')
plt.show()
print(f"[OK] Figura: {fig_path}")

print("\n" + "=" * 70)
print("Modelo v2 completado.")
print("=" * 70)
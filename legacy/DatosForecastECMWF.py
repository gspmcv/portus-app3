"""
Descarga forecast ECMWF IFS Open Data para el puerto de Palma de Mallorca
y genera un mapa con la malla del modelo y el punto extraído.
 
Versión v6:
- Detecta automáticamente el último run publicado (client.latest).
- Si un step devuelve 404 ("no existe aún"), aborta reintentos rápido
  en lugar de esperar 90s por mirror.
- El mapa usa solo matplotlib (sin cartopy).
"""
 
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
 
import numpy as np
import pandas as pd
import xarray as xr
from ecmwf.opendata import Client
 
# ---------- CONFIGURACIÓN ----------
PUNTO_LAT = 39.55          # Puerto de Palma de Mallorca
PUNTO_LON = 2.63
HORIZONTE_H = 120
PASO_H = 3
 
BASE_DIR = Path(r"C:\Users\pttmc\OneDrive\Desktop\03_Python-PTT\FORECAST")
GRIB_DIR = BASE_DIR / "grib"
CSV_DIR = BASE_DIR / "csv"
LOG_DIR = BASE_DIR / "logs"
 
for d in (GRIB_DIR, CSV_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)
 
MIRRORS = ["aws", "azure", "ecmwf"]
MAX_REINTENTOS_MIRROR = 3
SLEEP_ENTRE_STEPS = 2
 
GENERAR_MAPA = True
MAPA_LAT_MIN, MAPA_LAT_MAX = 38.8, 40.2
MAPA_LON_MIN, MAPA_LON_MAX = 1.8, 3.7
# -----------------------------------
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "descarga.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)
 
 
def _es_error_404(exc):
    """Detecta si la excepción corresponde a un 404 / recurso inexistente."""
    msg = str(exc).lower()
    return ("404" in msg
            or "not found" in msg
            or "does not exist" in msg
            or "nosuchkey" in msg)
 
 
def obtener_ultimo_run_disponible():
    """Consulta a ECMWF cuál es el último run publicado.
 
    Devuelve un datetime UTC con la fecha y hora del run, o None si
    ningún mirror responde.
    """
    for mirror in MIRRORS:
        try:
            client = Client(source=mirror)
            latest = client.latest(
                stream="oper", type="fc",
                param=["msl", "10u", "10v"],
                step=0,
            )
            log.info(f"Último run disponible ({mirror}): {latest} UTC")
            return latest, mirror
        except Exception as e:
            log.warning(f"No pude consultar 'latest' en {mirror}: {e}")
    return None, None
 
 
def descargar_step(step, fecha_run, hora_run, target, mirror_idx=0):
    """Descarga un step con fallback automático entre mirrors.
 
    - Un 404 aborta los reintentos en ese mirror inmediatamente.
    - Solo se reintenta con esperas largas en errores transitorios reales
      (timeouts, errores 5xx, problemas de red).
    """
    for intento in range(MAX_REINTENTOS_MIRROR):
        mirror = MIRRORS[mirror_idx]
        try:
            client = Client(source=mirror)
            client.retrieve(
                date=fecha_run, time=hora_run, step=step,
                stream="oper", type="fc",
                param=["msl", "10u", "10v"],
                target=str(target),
            )
            if target.exists() and target.stat().st_size > 100_000:
                log.info(f"  step {step:3d}h OK ({mirror}, "
                         f"{target.stat().st_size//1024} KB)")
                return True
            raise RuntimeError("archivo vacío o demasiado pequeño")
 
        except Exception as e:
            # Si el archivo se descargó bien pese al warning, lo damos por bueno
            if target.exists() and target.stat().st_size > 100_000:
                log.info(f"  step {step:3d}h OK ({mirror}, "
                         f"pese a warning: {target.stat().st_size//1024} KB)")
                return True
 
            # 404 => no existe, no reintentar en este mirror
            if _es_error_404(e):
                log.warning(f"  step {step:3d}h no encontrado en {mirror} "
                            f"(404). Salto reintentos.")
                if target.exists():
                    target.unlink()
                break  # ir al siguiente mirror
 
            # Error transitorio real: esperar y reintentar
            espera = 15 * (intento + 1)
            log.warning(f"  step {step:3d}h fallo en {mirror} "
                        f"(intento {intento+1}): {e}. Espero {espera}s")
            if target.exists():
                target.unlink()
            time.sleep(espera)
 
    # Probar siguiente mirror si queda
    if mirror_idx + 1 < len(MIRRORS):
        log.info(f"  cambiando a mirror {MIRRORS[mirror_idx+1]}")
        return descargar_step(step, fecha_run, hora_run,
                              target, mirror_idx + 1)
 
    log.error(f"  step {step}h FALLIDO en todos los mirrors")
    return False
 
 
def generar_mapa_malla(ds, lat_real, lon_real_plot, timestamp):
    """Mapa simple solo con matplotlib.
    Dibuja la malla del modelo y un contorno aproximado de Mallorca."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError:
        log.warning("matplotlib no instalado. Salto mapa.")
        return
 
    lats = ds.latitude.values
    lons = ds.longitude.values
    lons_plot = np.where(lons > 180, lons - 360, lons)
 
    # Filtrar nodos dentro de la ventana
    mask_lat = (lats >= MAPA_LAT_MIN) & (lats <= MAPA_LAT_MAX)
    mask_lon = (lons_plot >= MAPA_LON_MIN) & (lons_plot <= MAPA_LON_MAX)
    lats_v = lats[mask_lat]
    lons_v = lons_plot[mask_lon]
    LON_G, LAT_G = np.meshgrid(lons_v, lats_v)
 
    fig, ax = plt.subplots(figsize=(11, 9))
 
    # --- Fondo de mar ---
    ax.set_facecolor("#cfe2f3")
 
    # --- Contorno aproximado de Mallorca ---
    mallorca = [
        (2.36, 39.55), (2.42, 39.50), (2.48, 39.46), (2.59, 39.44),
        (2.75, 39.39), (2.92, 39.36), (3.05, 39.34), (3.18, 39.32),
        (3.27, 39.34), (3.37, 39.43), (3.46, 39.52), (3.48, 39.61),
        (3.45, 39.72), (3.36, 39.79), (3.22, 39.87), (3.14, 39.92),
        (3.05, 39.95), (2.93, 39.96), (2.81, 39.93), (2.70, 39.87),
        (2.60, 39.78), (2.50, 39.72), (2.42, 39.68), (2.36, 39.62),
        (2.36, 39.55),
    ]
    mx, my = zip(*mallorca)
    ax.fill(mx, my, facecolor="#f5e9d4", edgecolor="#8b7355",
            linewidth=1.2, zorder=2, label="_nolegend_")
 
    # Cabrera (al sur)
    cabrera = [(2.92, 39.13), (2.99, 39.12), (3.00, 39.16),
               (2.95, 39.18), (2.91, 39.16), (2.92, 39.13)]
    cx, cy = zip(*cabrera)
    ax.fill(cx, cy, facecolor="#f5e9d4", edgecolor="#8b7355",
            linewidth=1, zorder=2)
 
    # Pequeña porción de Menorca (NE)
    ax.fill([3.55, 3.70, 3.70, 3.55], [39.85, 39.85, 40.05, 40.05],
            facecolor="#f5e9d4", edgecolor="#8b7355",
            linewidth=1, zorder=2)
    ax.text(3.62, 39.95, "Menorca", fontsize=8, ha="center",
            zorder=7, style="italic")
 
    # --- Malla del modelo ---
    ax.scatter(LON_G, LAT_G, s=25, c="#333", marker="+",
               linewidth=1.0, zorder=4,
               label="Nodos malla ECMWF 0.25°")
 
    # --- Punto solicitado ---
    ax.plot(PUNTO_LON, PUNTO_LAT, marker="*", markersize=20,
            color="red", markeredgecolor="black", markeredgewidth=0.8,
            zorder=6, linestyle="",
            label=f"Punto solicitado ({PUNTO_LAT}, {PUNTO_LON})")
 
    # --- Nodo extraído ---
    ax.plot(lon_real_plot, lat_real, marker="o", markersize=14,
            color="lime", markeredgecolor="black", markeredgewidth=1.2,
            zorder=5, linestyle="",
            label=f"Nodo extraído ({lat_real:.2f}, {lon_real_plot:.2f})")
 
    # --- Línea entre ambos ---
    ax.plot([PUNTO_LON, lon_real_plot], [PUNTO_LAT, lat_real],
            color="red", linewidth=1.2, linestyle="--", zorder=5)
 
    # --- Celda 0.25° alrededor del nodo extraído ---
    rect = Rectangle((lon_real_plot - 0.125, lat_real - 0.125),
                     0.25, 0.25, linewidth=1.5,
                     edgecolor="lime", facecolor="lime", alpha=0.15,
                     zorder=3)
    ax.add_patch(rect)
 
    # --- Etiquetas ---
    etiquetas = [
        (2.65, 39.57, "Palma"),
        (3.13, 39.87, "Alcúdia"),
        (2.43, 39.55, "Andratx"),
        (3.20, 39.55, "Manacor"),
    ]
    for lon, lat, nombre in etiquetas:
        ax.text(lon, lat, nombre, fontsize=9, fontweight="bold",
                zorder=7,
                bbox=dict(boxstyle="round,pad=0.25",
                          facecolor="white", alpha=0.85,
                          edgecolor="gray", linewidth=0.5))
 
    # --- Estética general ---
    ax.set_xlim(MAPA_LON_MIN, MAPA_LON_MAX)
    ax.set_ylim(MAPA_LAT_MIN, MAPA_LAT_MAX)
    ax.set_aspect(1 / np.cos(np.radians(np.mean([MAPA_LAT_MIN, MAPA_LAT_MAX]))))
    ax.set_xlabel("Longitud (°E)", fontsize=10)
    ax.set_ylabel("Latitud (°N)", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4, zorder=1)
    ax.set_title("Malla ECMWF IFS Open Data (0.25°) — Bahía de Palma",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="upper left", framealpha=0.95, fontsize=9)
 
    plt.tight_layout()
    out_png = LOG_DIR / f"malla_modelo_{timestamp}.png"
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    log.info(f"Mapa guardado: {out_png}")
    plt.show()
 
 
def main():
    log.info("=" * 60)
    log.info("Inicio descarga forecast ECMWF IFS para Palma")
    log.info(f"Punto: lat={PUNTO_LAT}, lon={PUNTO_LON}")
    log.info(f"Carpeta base: {BASE_DIR}")
 
    # --- 1) Detectar el último run publicado ---
    latest_run, mirror_ok = obtener_ultimo_run_disponible()
    if latest_run is None:
        log.error("No se pudo determinar el último run disponible. Abortando.")
        return
 
    fecha_run = latest_run.strftime("%Y%m%d")
    hora_run = latest_run.strftime("%H%M")
    log.info(f"Usando run: {fecha_run} {hora_run} UTC")
 
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    run_dir = GRIB_DIR / f"run_{fecha_run}_{hora_run}"
    run_dir.mkdir(exist_ok=True)
 
    # --- 2) Descargar todos los steps ---
    steps = list(range(0, HORIZONTE_H + 1, PASO_H))
    archivos_ok = []
 
    for step in steps:
        target = run_dir / f"fc_step{step:03d}.grib2"
        if target.exists() and target.stat().st_size > 100_000:
            log.info(f"  step {step:3d}h en caché, salto")
            archivos_ok.append(target)
            continue
        if descargar_step(step,
                          fecha_run=int(fecha_run),
                          hora_run=int(hora_run),
                          target=target):
            archivos_ok.append(target)
        time.sleep(SLEEP_ENTRE_STEPS)
 
    if not archivos_ok:
        log.error("No se descargó ningún archivo. Abortando.")
        return
 
    log.info(f"Descargados {len(archivos_ok)}/{len(steps)} archivos. "
             "Extrayendo punto...")
 
    # --- 3) Extraer la serie en el punto ---
    lon_ecmwf = PUNTO_LON % 360
    registros = []
    lat_real = lon_real_plot = None
    ds_para_mapa = None
 
    for f in archivos_ok:
        try:
            ds = xr.open_dataset(f, engine="cfgrib",
                                 backend_kwargs={"indexpath": ""})
            punto = ds.sel(latitude=PUNTO_LAT,
                           longitude=lon_ecmwf,
                           method="nearest")
 
            if lat_real is None:
                lat_real = float(punto.latitude.values)
                lon_real = float(punto.longitude.values)
                lon_real_plot = lon_real if lon_real <= 180 else lon_real - 360
                dist_km = np.hypot(
                    (PUNTO_LAT - lat_real) * 111,
                    (PUNTO_LON - lon_real_plot) * 111 *
                    np.cos(np.radians(PUNTO_LAT))
                )
                log.info(f"Punto solicitado: ({PUNTO_LAT}, {PUNTO_LON})")
                log.info(f"Nodo extraído:    ({lat_real}, {lon_real_plot})")
                log.info(f"Distancia:        {dist_km:.2f} km")
                ds_para_mapa = xr.open_dataset(
                    f, engine="cfgrib",
                    backend_kwargs={"indexpath": ""}
                )
 
            t_valid = pd.Timestamp(punto.valid_time.values)
            registros.append({
                "time_utc": t_valid,
                "msl_Pa": float(punto.msl.values),
                "u10_ms": float(punto.u10.values),
                "v10_ms": float(punto.v10.values),
            })
            ds.close()
        except Exception as e:
            log.warning(f"  no pude leer {f.name}: {e}")
 
    if not registros:
        log.error("No se pudo extraer ningún dato")
        return
 
    df = pd.DataFrame(registros).sort_values("time_utc").reset_index(drop=True)
    df["msl_hPa"] = df["msl_Pa"] / 100.0
    df["wind_speed_ms"] = np.sqrt(df["u10_ms"]**2 + df["v10_ms"]**2)
    df["wind_dir_deg"] = (np.degrees(np.arctan2(-df["u10_ms"],
                                                -df["v10_ms"])) + 360) % 360
    df["lat_grid"] = lat_real
    df["lon_grid"] = lon_real_plot
 
    salida_csv = CSV_DIR / f"forcing_palma_{fecha_run}_{hora_run}.csv"
    df.to_csv(salida_csv, index=False, sep=";", decimal=",")
    log.info(f"Guardado: {salida_csv}")
    log.info(f"Filas: {len(df)} | "
             f"desde {df.time_utc.min()} hasta {df.time_utc.max()}")
 
    if GENERAR_MAPA and ds_para_mapa is not None:
        log.info("Generando mapa de la malla...")
        generar_mapa_malla(ds_para_mapa, lat_real, lon_real_plot,
                           f"{fecha_run}_{hora_run}")
        ds_para_mapa.close()
 
    log.info("=" * 60)
 
 
if __name__ == "__main__":
    main()
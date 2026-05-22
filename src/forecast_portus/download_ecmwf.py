from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import logging, time
import numpy as np
import pandas as pd
import xarray as xr
from ecmwf.opendata import Client

log = logging.getLogger(__name__)


def _is_404(exc):
    msg = str(exc).lower()
    return any(x in msg for x in ["404", "not found", "does not exist", "nosuchkey"])


def latest_run(mirrors=("aws", "azure", "ecmwf")):
    for mirror in mirrors:
        try:
            client = Client(source=mirror)
            latest = client.latest(stream="oper", type="fc", param=["msl", "10u", "10v"], step=0)
            return latest, mirror
        except Exception as exc:
            log.warning("No pude consultar latest en %s: %s", mirror, exc)
    raise RuntimeError("No se pudo determinar el último run ECMWF disponible")


def download_forecast_point(lat, lon, out_dir, horizon_h=120, step_h=3, mirrors=("aws", "azure", "ecmwf")):
    """Descarga ECMWF IFS Open Data y extrae una serie puntual de msl/u10/v10."""
    out_dir = Path(out_dir)
    grib_dir = out_dir / "ecmwf_grib"
    grib_dir.mkdir(parents=True, exist_ok=True)
    latest, _ = latest_run(mirrors)
    fecha_run = latest.strftime("%Y%m%d")
    hora_run = latest.strftime("%H%M")
    run_dir = grib_dir / f"run_{fecha_run}_{hora_run}"
    run_dir.mkdir(exist_ok=True)

    files = []
    for step in range(0, horizon_h + 1, step_h):
        target = run_dir / f"fc_step{step:03d}.grib2"
        if target.exists() and target.stat().st_size > 100_000:
            files.append(target)
            continue
        ok = False
        for mirror in mirrors:
            try:
                Client(source=mirror).retrieve(date=int(fecha_run), time=int(hora_run), step=step,
                                               stream="oper", type="fc", param=["msl", "10u", "10v"], target=str(target))
                ok = target.exists() and target.stat().st_size > 100_000
                if ok:
                    break
            except Exception as exc:
                if target.exists():
                    target.unlink()
                if _is_404(exc):
                    break
                time.sleep(5)
        if ok:
            files.append(target)

    if not files:
        raise RuntimeError("No se descargó ningún step ECMWF")

    lon_ecmwf = lon % 360
    registros, lat_real, lon_real_plot = [], None, None
    for f in files:
        ds = xr.open_dataset(f, engine="cfgrib", backend_kwargs={"indexpath": ""})
        p = ds.sel(latitude=lat, longitude=lon_ecmwf, method="nearest")
        if lat_real is None:
            lat_real = float(p.latitude.values)
            lon_real = float(p.longitude.values)
            lon_real_plot = lon_real if lon_real <= 180 else lon_real - 360
        registros.append({
            "time": pd.Timestamp(p.valid_time.values),
            "msl_Pa": float(p.msl.values),
            "u10": float(p.u10.values),
            "v10": float(p.v10.values),
            "lat_grid": lat_real,
            "lon_grid": lon_real_plot,
        })
        ds.close()
    df = pd.DataFrame(registros).sort_values("time").reset_index(drop=True)
    df["msl_hPa"] = df["msl_Pa"] / 100.0
    df["wind_speed"] = np.sqrt(df["u10"] ** 2 + df["v10"] ** 2)
    return df

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse

from .config import load_config, resolve
from .download_ecmwf import download_forecast_point
from .meteo_model import compute_meteo_tide
from .combine import load_astro_csv, combine_meteo_astro
from .plotting import plot_total_level


def main():
    parser = argparse.ArgumentParser(description="Pipeline MC VALNERA Forecast: ECMWF + meteo + astro")
    parser.add_argument("--config", default="config/config.example.yaml")
    parser.add_argument("--skip-download", action="store_true", help="Usa un CSV ECMWF ya procesado")
    parser.add_argument("--forecast-csv", default=None, help="CSV con time/msl/u10/v10 si no se descarga ECMWF")
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = Path(cfg["root"])
    processed = resolve(root, cfg["paths"]["processed_dir"])
    figures = resolve(root, cfg["paths"]["figures_dir"])
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    if args.skip_download:
        if not args.forecast_csv:
            raise SystemExit("Con --skip-download debes indicar --forecast-csv")
        import pandas as pd
        df_forcing = pd.read_csv(args.forecast_csv, parse_dates=["time"])
    else:
        df_forcing = download_forecast_point(
            lat=cfg["site"]["lat"], lon=cfg["site"]["lon"],
            out_dir=processed,
            horizon_h=cfg["forecast"]["horizon_h"], step_h=cfg["forecast"]["step_h"],
            mirrors=cfg["forecast"].get("mirrors", ["aws", "azure", "ecmwf"]),
        )
    forcing_csv = processed / f"forcing_ecmwf_{ts}.csv"
    df_forcing.to_csv(forcing_csv, index=False)

    m = cfg["model"]
    df_meteo = compute_meteo_tide(df_forcing, k_ib=m["k_ib"], alpha=m["alpha"], a_u=m["a_u"], a_v=m["a_v"])
    meteo_csv = processed / f"forecast_meteo_{ts}.csv"
    df_meteo.to_csv(meteo_csv, index=False)

    df_astro = load_astro_csv(resolve(root, cfg["paths"]["astro_csv"]))
    df_total = combine_meteo_astro(df_meteo, df_astro)
    total_csv = processed / f"forecast_nivel_total_{ts}.csv"
    df_total.to_csv(total_csv, index=False)

    fig = plot_total_level(df_total, figures / f"forecast_nivel_total_{ts}.png")
    print("OK")
    print(f"Forcing: {forcing_csv}")
    print(f"Meteo:   {meteo_csv}")
    print(f"Total:   {total_csv}")
    print(f"Figura:  {fig}")

if __name__ == "__main__":
    main()

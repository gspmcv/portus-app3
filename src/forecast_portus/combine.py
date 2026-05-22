from __future__ import annotations
import pandas as pd


def load_astro_csv(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path)
    col_time, col_val = raw.columns[0], raw.columns[1]
    # Formato tipo: 01-Jan-2026 00:00:00
    time = pd.to_datetime(raw[col_time], errors="coerce", format="%d-%b-%Y %H:%M:%S")
    if time.isna().all():
        time = pd.to_datetime(raw[col_time], errors="coerce")
    astro_m = pd.to_numeric(raw[col_val], errors="coerce")
    return pd.DataFrame({"time": time, "astro_m": astro_m, "astro_cm": astro_m * 100}).dropna()


def combine_meteo_astro(df_meteo: pd.DataFrame, df_astro: pd.DataFrame) -> pd.DataFrame:
    met = df_meteo.copy()
    met["time"] = pd.to_datetime(met["time"])
    if "eta_met" not in met.columns:
        raise ValueError("df_meteo debe incluir columna eta_met en metros")
    met = met[["time", "eta_met"]].rename(columns={"eta_met": "meteo_m"})
    met["meteo_cm"] = met["meteo_m"] * 100

    astro = df_astro.copy()
    astro["time"] = pd.to_datetime(astro["time"])
    df = met.merge(astro[["time", "astro_m", "astro_cm"]], on="time", how="inner").sort_values("time")
    if df.empty:
        raise RuntimeError("No hay solape temporal entre marea meteorológica y astronómica.")
    df["total_m"] = df["meteo_m"] + df["astro_m"]
    df["total_cm"] = df["meteo_cm"] + df["astro_cm"]
    df["residuo_m"] = df["total_m"] - df["astro_m"]
    df["residuo_cm"] = df["total_cm"] - df["astro_cm"]
    return df[["time", "meteo_cm", "astro_cm", "total_cm", "residuo_cm", "meteo_m", "astro_m", "total_m", "residuo_m"]]

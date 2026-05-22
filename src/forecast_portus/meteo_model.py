from __future__ import annotations
import numpy as np
import pandas as pd


def normalise_forecast_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres habituales de columnas ECMWF a los usados por el modelo."""
    out = df.copy()
    ren = {
        "time_utc": "time", "valid_time": "time",
        "u10_ms": "u10", "v10_ms": "v10",
        "wind_speed_ms": "wind_speed"
    }
    out = out.rename(columns={k: v for k, v in ren.items() if k in out.columns})
    if "msl_hPa" not in out.columns and "msl_Pa" in out.columns:
        out["msl_hPa"] = out["msl_Pa"] / 100.0
    if "wind_speed" not in out.columns and {"u10", "v10"}.issubset(out.columns):
        out["wind_speed"] = np.sqrt(out["u10"] ** 2 + out["v10"] ** 2)
    out["time"] = pd.to_datetime(out["time"])
    return out


def compute_meteo_tide(df: pd.DataFrame, k_ib=0.93, alpha=0.90, a_u=0.0, a_v=3.5e-4) -> pd.DataFrame:
    """Calcula marea meteorológica simplificada.

    eta_met(t) = alpha * eta_met(t-1) + (1-alpha) * [eta_IB(t) + eta_wind(t)]
    eta_IB = -0.00995 * k_IB * (P - P_ref)
    eta_wind = a_u*u10*|u10| + a_v*v10*|v10|
    """
    out = normalise_forecast_columns(df)
    required = {"time", "msl_hPa", "u10", "v10"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

    p_ref = out["msl_hPa"].mean()
    out["eta_IB"] = -0.00995 * k_ib * (out["msl_hPa"] - p_ref)
    out["eta_wind"] = a_u * out["u10"] * np.abs(out["u10"]) + a_v * out["v10"] * np.abs(out["v10"])
    out["eta_inst"] = out["eta_IB"] + out["eta_wind"]

    eta = np.zeros(len(out))
    eta[0] = out["eta_inst"].iloc[0]
    for i in range(1, len(out)):
        eta[i] = alpha * eta[i - 1] + (1 - alpha) * out["eta_inst"].iloc[i]
    out["eta_met"] = eta

    for col in ["eta_IB", "eta_wind", "eta_inst", "eta_met"]:
        out[f"{col}_cm"] = out[col] * 100.0
    return out

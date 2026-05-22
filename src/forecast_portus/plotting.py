from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def plot_total_level(df, out_png: str | Path):
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True, height_ratios=[2.5, 1])
    ax1.plot(df.time, df.total_m, lw=1.6, marker="o", ms=3, label="Nivel total (meteo + astro)")
    ax1.plot(df.time, df.astro_m, lw=1.4, marker="o", ms=3, label="Marea astronómica")
    ax1.set_ylabel("Nivel (m)")
    ax1.set_title("Forecast de nivel total del mar")
    ax1.grid(alpha=0.3)
    ax1.legend()

    ax2.plot(df.time, df.residuo_m, lw=1.4, marker="o", ms=2.5, label="Residuo / marea meteorológica")
    ax2.axhline(0, lw=0.7, alpha=0.6)
    ax2.set_ylabel("Residuo (m)")
    ax2.set_xlabel("Tiempo")
    ax2.grid(alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m %Hh"))
    for label in ax2.get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment("right")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    return out_png

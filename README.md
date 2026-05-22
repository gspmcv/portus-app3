# MC VALNERA Forecast — nivel total del mar

Repositorio preparado para demostrar un módulo experimental de forecast operativo basado en:

1. descarga automática de forecast meteorológico **ECMWF IFS Open Data**;
2. cálculo de marea meteorológica simplificada mediante presión, viento y persistencia;
3. combinación con marea astronómica externa;
4. generación de nivel total del mar previsto;
5. salida en CSV y figura para análisis/validación frente a observaciones tipo PORTUS.

## Estructura

```text
config/                 Configuración del punto, coeficientes y rutas
src/forecast_portus/    Código modular del pipeline
scripts/                Scripts de ejecución
data/raw/astro/         Serie de marea astronómica de entrada
data/raw/portus/        Plantillas para observaciones PORTUS
legacy/                 Scripts originales conservados como referencia
outputs/figures/        Figuras generadas
data/processed/         CSV generados por el pipeline
```

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

> Nota: para leer GRIB se usa `cfgrib`. En algunos equipos puede requerir instalar `ecCodes`.

## Ejecución completa

```bash
python scripts/01_run_pipeline.py --config config/config.example.yaml
```

El proceso descarga el último run disponible de ECMWF, extrae presión y viento en el punto configurado, calcula la marea meteorológica, la combina con la marea astronómica y genera outputs.

## Ejecución sin descarga

Si ya tienes un CSV procesado con `time`, `msl_hPa`, `u10` y `v10`:

```bash
python scripts/01_run_pipeline.py --skip-download --forecast-csv data/processed/mi_forcing.csv
```

## Modelo meteorológico

El cálculo principal es:

```text
eta_met(t) = alpha · eta_met(t-1) + (1-alpha) · [eta_IB(t) + eta_wind(t)]
eta_IB    = -0.00995 · k_IB · (P - P_ref)
eta_wind  = a_u · u10 · |u10| + a_v · v10 · |v10|
```

El nivel total se obtiene como:

```text
nivel_total = marea_meteorológica + marea_astronómica
```

## Uso en la memoria técnica

Este repositorio permite enseñar una capacidad propia de MC VALNERA para automatizar la descarga, procesado y combinación de datos meteorológicos y astronómicos, generando un forecast operativo simplificado contrastable con observaciones PORTUS.

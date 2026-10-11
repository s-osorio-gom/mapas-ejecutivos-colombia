#!/usr/bin/env python3
"""
demo.py — un mapa ejecutivo completo sobre datos sintéticos.

    python3 ejemplo/demo.py
    python3 ejemplo/demo.py --shp ruta/a/MGN_ADM_DPTO_POLITICO.shp

Sin `--shp` funciona igual: la capa de departamentos es opcional y el ejemplo
no obliga a nadie a descargar 1,4 GB de cartografía para ver cómo se ve esto.
Con `--shp` se añade el contorno oficial. Ver `docs/cartografia-dane.md`.

Los datos son inventados. No hay información de ninguna empresa en este
repositorio.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from mapa_ejecutivo import MapaEjecutivo, por_cuantiles  # noqa: E402
from mapa_ejecutivo.preparar import validar_coordenadas  # noqa: E402
from mapa_ejecutivo.validar import verificar  # noqa: E402

SALIDA = RAIZ / "ejemplo" / "salida"

# Ciudades reales solo para que el fondo tenga sentido; los puntos son ficticios.
CIUDADES = [("Bogotá", 4.65, -74.08, 420), ("Medellín", 6.24, -75.58, 260),
            ("Cali", 3.44, -76.52, 200), ("Barranquilla", 10.97, -74.80, 140),
            ("Bucaramanga", 7.12, -73.12, 110), ("Pereira", 4.81, -75.69, 90),
            ("Villavicencio", 4.14, -73.63, 70), ("Montería", 8.75, -75.88, 60)]


def datos_sinteticos(semilla=7) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    filas = []
    for ciudad, lat, lon, n in CIUDADES:
        s = 0.055
        filas.append(pd.DataFrame({
            "ciudad": ciudad,
            "lat": np.round(lat + rng.normal(0, s, n), 6),
            "lon": np.round(lon + rng.normal(0, s, n), 6),
            "venta_mes": np.round(rng.lognormal(np.log(3.2e6), 0.95, n), -3),
        }))
    df = pd.concat(filas, ignore_index=True)
    df.insert(0, "cliente", [f"Cliente {i:04d}" for i in range(1, len(df) + 1)])
    df["canal"] = rng.choice(["Tienda", "Minimercado", "Autoservicio"],
                             len(df), p=[.6, .3, .1])
    # Basura realista: dos filas sin coordenada y dos con lat/lon invertidas.
    df.loc[3, ["lat", "lon"]] = [np.nan, np.nan]
    df.loc[7, ["lat", "lon"]] = [0.0, 0.0]
    df.loc[11, ["lat", "lon"]] = [df.loc[11, "lon"], df.loc[11, "lat"]]
    df.loc[19, ["lat", "lon"]] = [df.loc[19, "lon"], df.loc[19, "lat"]]
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shp", help="shapefile de departamentos del DANE (opcional)")
    a = ap.parse_args()

    df = datos_sinteticos()
    print(f"\n  {len(df):,} registros sintéticos en {df.ciudad.nunique()} ciudades")

    limpio, _ = validar_coordenadas(df, "lat", "lon")

    rangos = por_cuantiles(limpio.venta_mes, n=4)
    print("  Rangos por cuartil:")
    for r in rangos:
        print(f"    {r.etiqueta}")

    m = MapaEjecutivo(
        limpio, lat="lat", lon="lon", valor="venta_mes", nombre="cliente",
        titulo="PUNTOS DE VENTA", subtitulo="Datos sintéticos · ejemplo reproducible",
        rangos=rangos,
        popup=[("Ciudad", "ciudad"), ("Canal", "canal"), ("Venta del mes", "venta_mes")],
    )
    if a.shp:
        print(f"  Cartografía: {Path(a.shp).name}")
        m.capa_departamentos(a.shp)

    ruta = m.guardar(SALIDA / "mapa_nacional.html")
    print(f"\n  Escrito {ruta.relative_to(RAIZ)} "
          f"({ruta.stat().st_size/1e6:.1f} MB)\n")

    ok = verificar(ruta, limpio, valor="venta_mes", rangos=rangos, nombre="cliente")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

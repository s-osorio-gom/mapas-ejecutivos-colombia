"""
preparar.py — validar coordenadas antes de dibujar nada.

La mitad de los mapas que salen mal no tienen un problema de mapa: tienen un
problema de base. Latitud y longitud invertidas, comas decimales leídas como
miles, ceros que en realidad son "no sé dónde queda". Todo eso se ve como
puntos en el Golfo de Guinea o en mitad del Pacífico.
"""
from __future__ import annotations

import pandas as pd

from .mapa import COLOMBIA


def validar_coordenadas(df: pd.DataFrame, lat: str = "lat", lon: str = "lon",
                        bbox: dict | None = None, verbose: bool = True):
    """Devuelve (df_válidas, informe). No corrige nada por su cuenta: avisa."""
    bbox = bbox or COLOMBIA
    faltan = [c for c in (lat, lon) if c not in df.columns]
    if faltan:
        raise KeyError(f"columnas de coordenadas que no están en el DataFrame: {faltan}")
    faltan = {"lat_min", "lat_max", "lon_min", "lon_max"} - set(bbox)
    if faltan:
        raise KeyError(f"al bbox le faltan las llaves {sorted(faltan)}")
    d = df.copy()
    d[lat] = pd.to_numeric(d[lat], errors="coerce")
    d[lon] = pd.to_numeric(d[lon], errors="coerce")

    nulas = d[lat].isna() | d[lon].isna()
    cero = (d[lat] == 0) & (d[lon] == 0)
    dentro = (d[lat].between(bbox["lat_min"], bbox["lat_max"])
              & d[lon].between(bbox["lon_min"], bbox["lon_max"]))
    # (0, 0) es "no sé dónde queda" aunque un bbox propio lo contenga.
    validas = dentro & ~nulas & ~cero

    # Sospecha de lat/lon invertidas: no caen dentro, pero al cambiarlas sí.
    invertidas = (~dentro & ~nulas
                  & d[lon].between(bbox["lat_min"], bbox["lat_max"])
                  & d[lat].between(bbox["lon_min"], bbox["lon_max"]))

    informe = {
        "filas": len(d),
        "sin_coordenada": int(nulas.sum()),
        "en_cero": int(cero.sum()),
        "fuera_del_area": int((~dentro & ~nulas).sum()),
        "posible_lat_lon_invertida": int(invertidas.sum()),
        "utilizables": int(validas.sum()),
    }
    if verbose:
        print("\n  Coordenadas")
        for k, v in informe.items():
            marca = "  " if k in ("filas", "utilizables") or v == 0 else "⚠ "
            print(f"    {marca}{k.replace('_', ' '):<28} {v:>8,}")
        if informe["posible_lat_lon_invertida"]:
            print("      → revise si esas filas traen latitud y longitud al revés")
        print()
    return d[validas].copy(), informe

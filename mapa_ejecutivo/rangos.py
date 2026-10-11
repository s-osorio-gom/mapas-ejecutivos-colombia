"""
rangos.py — cómo se parte una métrica en categorías y con qué colores se pintan.

Dos reglas que no se negocian y explican por qué esto no es un `matplotlib` con
colores bonitos:

1. **Paleta secuencial de un solo tono.** De claro a oscuro dentro de la misma
   familia. Un mapa donde el rojo, el verde y el azul marcan *cantidades*
   obliga a mirar la leyenda en cada punto; una escala de un tono se lee sin
   leyenda. Los colores distintos se reservan para categorías que no tienen
   orden (una región, un dueño), nunca para magnitudes.

2. **El tamaño del punto acompaña al color.** Refuerza la jerarquía sin meter
   una segunda variable visual, y salva el mapa para quien no distingue bien
   los tonos.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# ColorBrewer Blues. Probada para daltonismo y legible impresa en gris.
AZULES = ["#C6DBEF", "#6BAED6", "#2171B5", "#08306B"]
VERDES = ["#C7E9C0", "#74C476", "#238B45", "#00441B"]
GRISES = ["#D9D9D9", "#969696", "#525252", "#252525"]
SIN_DATO = "#BDBDBD"


@dataclass(frozen=True)
class Rango:
    """Un escalón de la escala."""
    etiqueta: str
    desde: float
    hasta: float          # exclusivo; usar float("inf") en el último
    color: str
    radio: float

    def contiene(self, v: float) -> bool:
        return self.desde <= v < self.hasta


def por_cuantiles(valores, n: int = 4, paleta=None,
                  radios=(4, 5.5, 7, 9), moneda: str = "$",
                  divisor: float = 1e6, sufijo: str = "M") -> list[Rango]:
    """Corta en `n` grupos de tamaño parecido y arma las etiquetas solas.

    Cortar por cuantiles y no en números redondos evita el mapa que sale
    entero del color más claro porque alguien eligió los cortes a ojo pensando
    en los clientes grandes.
    """
    paleta = paleta or AZULES
    if n < 1:
        raise ValueError("n debe ser al menos 1")
    # Repetir colores o radios rompería la escala de un tono —dos rangos con
    # el mismo color no se distinguen— y el conteo por color de `verificar`.
    if n > len(paleta) or n > len(radios):
        raise ValueError(f"n={n} pide más rangos que colores ({len(paleta)}) "
                         f"o radios ({len(radios)}) disponibles")
    v = pd.to_numeric(pd.Series(valores), errors="coerce").dropna()
    v = v[np.isfinite(v) & (v > 0)]
    if v.empty:
        return []
    internos = np.quantile(v, np.linspace(1 / n, 1, n))[:-1]
    # Con muchos valores repetidos dos cuantiles coinciden y quedaría un rango
    # vacío del tipo «$1.0M – $1.0M». Se fusionan: salen menos rangos, no falsos.
    # Un corte igual al mínimo deja vacío el primer rango: también se descarta.
    cortes = [0.0, *sorted({float(x) for x in internos if x > v.min()}), float("inf")]
    n = len(cortes) - 1

    def et(a, b):
        fa = f"{moneda}{a/divisor:,.1f}{sufijo}"
        return (f"desde {fa}" if b == float("inf")
                else f"{fa} – {moneda}{b/divisor:,.1f}{sufijo}")

    return [Rango(f"{i+1} · {et(cortes[i], cortes[i+1])}", cortes[i], cortes[i + 1],
                  paleta[i % len(paleta)], radios[i % len(radios)])
            for i in range(n)]


def clasificar(valores, rangos: list[Rango]) -> pd.Series:
    """Índice del rango de cada valor; -1 si no cae en ninguno (o es nulo)."""
    v = pd.to_numeric(pd.Series(valores), errors="coerce")
    out = pd.Series(-1, index=v.index, dtype=int)
    for i, r in enumerate(rangos):
        out[v.between(r.desde, r.hasta, inclusive="left")] = i
    return out

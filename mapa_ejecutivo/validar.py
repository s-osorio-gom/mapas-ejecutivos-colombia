"""
validar.py — comprobar el HTML contra la base que lo originó.

Un mapa puede verse perfecto y estar mostrando otra cosa. Estas pruebas leen el
archivo generado y lo confrontan con el DataFrame:

    ¿hay un punto por fila?           conteo de marcadores
    ¿cada rango tiene los suyos?      conteo por color
    ¿el más grande aparece?           búsqueda del registro tope
    ¿se puede compartir por correo?   tamaño del archivo

No sustituye mirar el mapa. Detecta que faltan 300 puntos; no detecta que la
leyenda tapa Bogotá.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import rangos as R
from .mapa import _esc, _nombre


def verificar(html: str | Path, df: pd.DataFrame, valor: str | None = None,
              rangos: list[R.Rango] | None = None, nombre: str | None = None,
              tope_mb: float = 5.0) -> bool:
    ruta = Path(html)
    texto = ruta.read_text(encoding="utf-8")
    mb = ruta.stat().st_size / 1e6
    fallos = []

    def prueba(titulo, ok, detalle=""):
        print(f"  [{'OK  ' if ok else 'FALLA'}] {titulo}" + (f" — {detalle}" if detalle else ""))
        if not ok:
            fallos.append(titulo)

    # Se cuenta en las opciones de cada marcador, no en todo el archivo: así
    # ni la leyenda, ni el color de marca, ni un texto del usuario que repita
    # un código de color o la palabra «circleMarker» alteran el conteo.
    rellenos = re.findall(r'L\.circleMarker\(\s*\[[^\]]*\],\s*\{[^}]*?"fillColor":\s*"([^"]+)"',
                          texto)
    # Si una versión de folium cambiara el formato, esto da 0 y la prueba falla
    # a la vista: nunca pasa en silencio.
    marcadores = len(rellenos)
    prueba("un marcador por fila", marcadores == len(df),
           f"{marcadores:,} en el HTML · {len(df):,} en la base")

    if valor and rangos:
        clase = R.clasificar(df[valor], rangos)
        for i, r in enumerate(rangos):
            esperado = int((clase == i).sum())
            hallado = sum(c.lower() == r.color.lower() for c in rellenos)
            prueba(f"rango «{r.etiqueta}»", hallado == esperado,
                   f"{hallado} pintados · {esperado} esperados")

    if nombre and valor and nombre in df.columns and valor in df.columns:
        v = pd.to_numeric(df[valor], errors="coerce")
        if v.notna().any():
            # En el HTML el nombre va escapado (ver mapa._esc).
            top = _nombre(df.loc[v.idxmax(), nombre])
            prueba("el registro más grande aparece", _esc(top) in texto, top)

    prueba(f"pesa menos de {tope_mb:g} MB", mb <= tope_mb,
           f"{mb:.1f} MB" + ("" if mb <= tope_mb else " — simplifique más la geometría"))
    prueba("sin 'NaN' visible", "NaN" not in texto)

    print(f"\n  {len(fallos)} fallos\n")
    return not fallos

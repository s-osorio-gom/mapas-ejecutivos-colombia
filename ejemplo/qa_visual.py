#!/usr/bin/env python3
"""
qa_visual.py — abrir el mapa en un navegador de verdad y mirarlo.

    python3 ejemplo/qa_visual.py

`mapa_ejecutivo.validar` comprueba que los números cuadren. Esto comprueba que
la página abra, pinte y no tenga errores — y deja capturas, que es el único
modo de ver que la leyenda tapa una ciudad o que un rótulo quedó cortado.

    pip install playwright && playwright install chromium
"""
from pathlib import Path

SALIDA = Path(__file__).resolve().parent / "salida"
MAPA = SALIDA / "mapa_nacional.html"


def main() -> int:
    if not MAPA.exists():
        print(f"Falta {MAPA}. Corra antes: python3 ejemplo/demo.py")
        return 1
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Falta playwright:  pip install playwright && playwright install chromium")
        return 1

    errores, fallidas = [], []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.on("requestfailed", lambda r: fallidas.append(r.url))

        pg.goto(MAPA.as_uri())
        pg.wait_for_selector(".leaflet-container", timeout=30_000)
        pg.wait_for_timeout(4_500)
        # Con racimos activos no hay trazos en la vista nacional: los puntos son
        # iconos HTML. Contar solo `path` daba cero sobre un mapa perfecto.
        formas = pg.evaluate(
            "document.querySelectorAll('path.leaflet-interactive').length"
            " + document.querySelectorAll('.leaflet-marker-icon').length")
        texto = pg.inner_text("body")
        pg.screenshot(path=str(SALIDA / "qa_01_nacional.png"))

        # Acercar a la ciudad más densa para ver los puntos sueltos
        pg.evaluate("""() => {
            const k = Object.keys(window).find(k => k.startsWith('map_'));
            window[k].setView([4.65, -74.08], 13);
        }""")
        pg.wait_for_timeout(3_000)
        pg.screenshot(path=str(SALIDA / "qa_02_ciudad.png"))
        nav.close()

    print(f"  formas dibujadas    {formas}")
    print(f"  errores de JS       {len(errores)}")
    for e in errores[:5]:
        print(f"      · {e}")
    print(f"  peticiones fallidas {len(fallidas)}")
    for u in fallidas[:3]:
        print(f"      · {u}")
    for t in ("PUNTOS DE VENTA", "Total"):
        print(f"  «{t}» en pantalla   {'OK' if t in texto else 'FALTA'}")
    print(f"  'NaN' en pantalla   {'SÍ ← defecto' if 'NaN' in texto else 'no'}")
    print("  capturas en ejemplo/salida/qa_*.png — MIRARLAS")
    return 1 if errores or not formas else 0


if __name__ == "__main__":
    raise SystemExit(main())

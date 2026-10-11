"""
mapa.py — un mapa ejecutivo en un solo archivo HTML.

    from mapa_ejecutivo import MapaEjecutivo, rangos

    m = MapaEjecutivo(df, lat="lat", lon="lon", valor="venta",
                      titulo="Puntos de venta", subtitulo="Enero 2026")
    m.capa_departamentos("ruta/MGN_ADM_DPTO_POLITICO.shp")   # opcional
    m.guardar("mapa.html")

El resultado abre con doble clic, sin servidor. Los datos van dentro del
archivo; las librerías de Leaflet (CDN) y las teselas del fondo se cargan de
internet al abrirlo, así que sin conexión el mapa no se pinta.
"""
from __future__ import annotations

import html as _html
import numbers
import re
from pathlib import Path

import folium
import numpy as np
import pandas as pd
from folium.plugins import Fullscreen, MarkerCluster, MeasureControl, MousePosition

from . import rangos as R

# Fondo gris claro de Esri, sin llave.
#
# El fondo habitual de Folium para mapas ejecutivos era CartoDB Positron. Pasó a
# exigir clave de API: sin ella devuelve teselas estampadas con "API KEY
# REQUIRED" y el mapa parece roto — sin un solo error en la consola del
# navegador. Se descubre mirando una captura, no revisando logs.
FONDO = ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/"
         "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}")
FONDO_ATTR = "Esri · HERE · Garmin · OpenStreetMap contributors"
DANE_ATTR = "Límites: DANE, Marco Geoestadístico Nacional"

COLOMBIA = dict(lat_min=-4.5, lat_max=13.5, lon_min=-82.0, lon_max=-66.0)

# Racimo en el tono de la marca; el tamaño crece con la cantidad.
_RACIMO_JS = """
function (cluster) {
  var n = cluster.getChildCount();
  var d = n < 50 ? 34 : n < 200 ? 42 : 50;
  return new L.DivIcon({
    // `font` va antes que `line-height`: el atajo `font` lo reinicia, y el
    // número quedaba pegado arriba del círculo en vez de centrado.
    html: '<div style="width:' + d + 'px;height:' + d + 'px;'
        + 'font:600 12px -apple-system,Segoe UI,Arial,sans-serif;'
        + 'line-height:' + d + 'px;'
        + 'border-radius:50%%;background:%s;color:#fff;text-align:center;'
        + 'box-shadow:0 0 0 4px rgba(31,78,121,.20)">' + n + '</div>',
    className: '', iconSize: new L.Point(d, d)
  });
}
"""

_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _esc(v) -> str:
    """Escapa un texto del usuario antes de meterlo en el HTML del mapa.

    Folium pone popups y tooltips dentro de plantillas de JavaScript entre
    comillas invertidas, así que además de `<`, `>`, `&` y comillas hay que
    neutralizar la comilla invertida, `$` y la barra invertida: un nombre de
    cliente como `${alert(1)}` se ejecutaría al abrir el mapa.
    """
    return (_html.escape(str(v), quote=True)
            .replace("`", "&#96;").replace("$", "&#36;").replace("\\", "&#92;"))


def _color(c, donde: str) -> str:
    """Los colores van a CSS y a JavaScript: solo se aceptan hexadecimales."""
    if not isinstance(c, str) or not _COLOR.match(c):
        raise ValueError(f"{donde}: el color {c!r} no es hexadecimal (#RGB o #RRGGBB)")
    return c


class MapaEjecutivo:
    def __init__(self, df: pd.DataFrame, lat: str, lon: str, valor: str | None = None,
                 titulo: str = "", subtitulo: str = "", rangos: list[R.Rango] | None = None,
                 popup: list[tuple[str, str]] | None = None, nombre: str | None = None,
                 color_marca: str = "#1F4E79", agrupar_desde: int | None = 600):
        """
        `popup`  — [(etiqueta visible, columna), …]; si falta, se arma solo.
        `nombre` — columna que titula el globo de información.
        `agrupar_desde` — a partir de cuántos puntos se agrupan en racimos; los
                          racimos se abren al acercarse. `None` los desactiva.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df debe ser un pandas.DataFrame")
        faltan = [c for c in (lat, lon, valor, nombre) if c is not None and c not in df.columns]
        faltan += [c for _, c in (popup or []) if c not in df.columns and c not in faltan]
        if faltan:
            raise KeyError(f"columnas que no están en el DataFrame: {faltan}")
        if df.empty:
            raise ValueError("el DataFrame no tiene filas: no hay nada que dibujar")
        # Una coordenada nula o no numérica llega al navegador como NaN y el
        # mapa no encuadra. Se rechaza aquí con un mensaje que dice qué hacer.
        coords = df[[lat, lon]].apply(pd.to_numeric, errors="coerce").astype(float)
        malas = int(((~np.isfinite(coords.to_numpy())).any(axis=1)
                     | (coords[lat].abs() > 90).to_numpy()
                     | (coords[lon].abs() > 180).to_numpy()).sum())
        if malas:
            raise ValueError(f"{malas:,} filas sin latitud/longitud numérica válida; "
                             "páselas antes por preparar.validar_coordenadas()")
        self.df = df.reset_index(drop=True)
        self.df[lat] = coords[lat].to_numpy()
        self.df[lon] = coords[lon].to_numpy()
        self.lat, self.lon, self.valor = lat, lon, valor
        self.titulo, self.subtitulo = titulo, subtitulo
        self.color_marca = _color(color_marca, "color_marca")
        self.nombre = nombre
        self.popup = popup or [(c, c) for c in df.columns[:6] if c not in (lat, lon)]
        self.agrupar_desde = agrupar_desde
        # Todo se calcula sobre self.df, que ya viene reindexado. Usar el `df`
        # de entrada aquí deja `clase` con el índice original: si venía filtrado
        # —y suele venir, de validar_coordenadas— las etiquetas no coinciden
        # con las posiciones y el dibujo revienta o, peor, pinta otra fila.
        self.rangos = (rangos if rangos is not None else
                       (R.por_cuantiles(self.df[valor]) if valor else []))
        if self.rangos and not valor:
            raise ValueError("se pasaron `rangos` sin la columna `valor` que clasifican")
        for r in self.rangos:
            _color(r.color, f"rango «{r.etiqueta}»")
        self.clase = (R.clasificar(self.df[valor], self.rangos) if self.rangos
                      else pd.Series(-1, index=self.df.index))
        self._capas: list[tuple[str, object, dict]] = []

    # ── capas territoriales ─────────────────────────────────────────────────
    def capa_departamentos(self, shp, simplificar: float = 0.005,
                           atribucion: str = DANE_ATTR, **estilo):
        """Contorno de departamentos desde un shapefile oficial.

        `simplificar` es lo que decide si el HTML pesa 3 MB o 44: la geometría
        del DANE sin simplificar arrastra un detalle que a escala nacional no
        se ve. 0,005 grados es imperceptible en pantalla.
        """
        return self._capa_shape("Departamentos", shp, simplificar,
                                {"color": "#8A949F", "weight": 1.1, "fill": False, **estilo},
                                atribucion=atribucion)

    def capa_municipios(self, shp, simplificar: float = 0.001, bbox=None,
                        atribucion: str = DANE_ATTR, **estilo):
        return self._capa_shape("Municipios", shp, simplificar,
                                {"color": "#C2C9D1", "weight": 0.5, "fill": False, **estilo},
                                bbox=bbox, mostrar=False, atribucion=atribucion)

    def _capa_shape(self, nombre, shp, simplificar, estilo, bbox=None, mostrar=True,
                    atribucion=""):
        try:
            import geopandas as gpd
        except ImportError as e:
            raise ImportError("las capas territoriales necesitan geopandas: "
                              "pip install -e '.[territorial]'") from e
        gdf = gpd.read_file(shp)
        if gdf.crs is None:
            # Sin .prj no se sabe en qué sistema vienen; adivinar pone Bogotá
            # en el Atlántico. Mejor un error que un mapa corrido.
            raise ValueError(f"{shp}: la capa no declara sistema de coordenadas "
                             "(¿falta el archivo .prj?)")
        gdf = gdf.to_crs(epsg=4326)
        if bbox:
            gdf = gdf.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
        if simplificar:
            gdf["geometry"] = gdf.geometry.simplify(simplificar, preserve_topology=True)
        self._capas.append((nombre, gdf, {"estilo": estilo, "mostrar": mostrar,
                                          "atribucion": atribucion}))
        return self

    # ── armado ──────────────────────────────────────────────────────────────
    def _globo(self, fila) -> str:
        titulo = _esc(_nombre(fila.get(self.nombre))) if self.nombre else ""
        filas = "".join(
            f"<tr><td style='padding:3px 12px 3px 0;color:#667'>{_esc(et)}</td>"
            f"<td style='padding:3px 0;text-align:right;font-weight:600'>"
            f"{_esc(_fmt(fila.get(col)))}</td></tr>"
            for et, col in self.popup if col in fila.index)
        cab = (f"<div style='background:{self.color_marca};color:#fff;padding:8px 10px;"
               f"margin:-9px -9px 8px -9px;border-radius:4px 4px 0 0;font-size:13px;"
               f"font-weight:600'>{titulo}</div>") if titulo else ""
        return (f"<div style=\"font:12px/1.45 -apple-system,'Segoe UI',Arial,sans-serif;"
                f"min-width:250px\">{cab}<table style='width:100%'>{filas}</table></div>")

    def _leyenda(self) -> str:
        if not self.rangos:
            return ""
        filas = ""
        for i, r in enumerate(self.rangos):
            n = int((self.clase == i).sum())
            filas += (f"<tr><td style='padding:2px 8px 2px 0'>"
                      f"<span style='display:inline-block;width:11px;height:11px;"
                      f"border-radius:50%;background:{r.color};border:1px solid #fff;"
                      f"box-shadow:0 0 0 1px #bbb'></span></td>"
                      f"<td style='padding:2px 10px 2px 0'>{_esc(r.etiqueta)}</td>"
                      f"<td style='text-align:right;font-weight:600'>{n:,}</td></tr>")
        sin = int((self.clase < 0).sum())
        if sin:
            filas += (f"<tr><td><span style='display:inline-block;width:11px;height:11px;"
                      f"border-radius:50%;background:{R.SIN_DATO}'></span></td>"
                      f"<td>Sin dato</td><td style='text-align:right'>{sin:,}</td></tr>")
        total = f"<tr><td></td><td style='padding-top:5px;border-top:1px solid #ddd'>Total</td>" \
                f"<td style='padding-top:5px;border-top:1px solid #ddd;text-align:right;" \
                f"font-weight:700'>{len(self.df):,}</td></tr>"
        return (f"<div style=\"position:fixed;bottom:22px;left:12px;z-index:9999;"
                f"background:#fff;border:1px solid #d7dbe0;border-radius:8px;padding:10px 12px;"
                f"font:11.5px/1.4 -apple-system,'Segoe UI',Arial,sans-serif;"
                f"box-shadow:0 2px 10px rgba(0,0,0,.12)\">"
                f"<table>{filas}{total}</table></div>")

    def _titulo(self) -> str:
        if not self.titulo:
            return ""
        return (f"<div style=\"position:fixed;top:12px;left:50%;transform:translateX(-50%);"
                f"z-index:9999;background:#fff;border:1px solid #d7dbe0;border-radius:8px;"
                f"padding:8px 18px;text-align:center;"
                f"font-family:-apple-system,'Segoe UI',Arial,sans-serif;"
                f"box-shadow:0 2px 10px rgba(0,0,0,.12)\">"
                f"<div style='font-size:14px;font-weight:700;color:{self.color_marca}'>"
                f"{_esc(self.titulo)}</div>"
                f"<div style='font-size:11px;color:#6b7280'>{_esc(self.subtitulo)}</div></div>")

    def construir(self) -> folium.Map:
        m = folium.Map(tiles=None, control_scale=True)
        # La cartografía oficial se cita en el mismo rótulo que el fondo.
        fuentes = dict.fromkeys(c["atribucion"] for _, _, c in self._capas if c["atribucion"])
        attr = " · ".join([FONDO_ATTR, *(_esc(f) for f in fuentes)])
        folium.TileLayer(tiles=FONDO, attr=attr, name="Fondo", control=False).add_to(m)

        for nombre, gdf, cfg in self._capas:
            folium.GeoJson(gdf.to_json(), name=nombre, show=cfg["mostrar"],
                           style_function=lambda _f, e=cfg["estilo"]: e).add_to(m)

        capa = folium.FeatureGroup(name="Puntos", show=True)
        destino = capa
        if self.agrupar_desde and len(self.df) >= self.agrupar_desde:
            # Los racimos van en el tono de la marca, no en el verde-amarillo-rojo
            # que trae el plugin por defecto: esos colores codifican "cuántos",
            # y compiten con la escala de la leyenda, que codifica "cuánto".
            # Dos escalas de color en el mismo mapa significan que ninguna se lee.
            destino = MarkerCluster(
                disableClusteringAtZoom=10,
                icon_create_function=_RACIMO_JS % (self.color_marca,),
            ).add_to(capa)

        # De menor a mayor: los puntos grandes quedan encima y no los tapan los
        # chicos, que en zona densa es la diferencia entre ver los clientes que
        # importan y ver una mancha.
        for i in self.clase.sort_values(kind="stable").index:
            fila = self.df.loc[i]
            k = int(self.clase[i])
            color = self.rangos[k].color if k >= 0 else R.SIN_DATO
            radio = self.rangos[k].radio if k >= 0 else 4
            folium.CircleMarker(
                [float(fila[self.lat]), float(fila[self.lon])], radius=radio,
                color="#ffffff", weight=1, fill=True, fill_color=color, fill_opacity=0.9,
                popup=folium.Popup(self._globo(fila), max_width=360),
                tooltip=(_esc(_nombre(fila.get(self.nombre))) or None)
                if self.nombre else None,
            ).add_to(destino)
        capa.add_to(m)

        m.fit_bounds([[float(self.df[self.lat].min()), float(self.df[self.lon].min())],
                      [float(self.df[self.lat].max()), float(self.df[self.lon].max())]],
                     padding=(25, 25))
        Fullscreen(position="topleft").add_to(m)
        MeasureControl(position="topleft", primary_length_unit="kilometers").add_to(m)
        MousePosition(position="bottomright", num_digits=4,
                      empty_string="").add_to(m)
        folium.LayerControl(collapsed=True).add_to(m)
        for html in (self._titulo(), self._leyenda()):
            if html:
                m.get_root().html.add_child(folium.Element(html))
        return m

    def guardar(self, ruta) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.construir().save(str(ruta))
        return ruta


def _fmt(v, vacio: str = "—") -> str:
    # pd.NA, NaT, None y NaN (de Python o de numpy) son "sin dato", no "nan".
    if v is None or (not isinstance(v, (str, bytes)) and pd.api.types.is_scalar(v)
                     and pd.isna(v)):
        return vacio
    # numbers.Real cubre también los escalares de numpy (np.int64 no es `int`).
    if isinstance(v, numbers.Real) and not isinstance(v, (bool, np.bool_)):
        v = float(v)
        if v in (float("inf"), float("-inf")):
            return vacio
        return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


def _nombre(v) -> str:
    """El nombre se muestra tal cual (un código no lleva separador de miles)."""
    return "" if _fmt(v, vacio="") == "" else str(v)

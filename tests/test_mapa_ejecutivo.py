"""Pruebas de la librería. Corren sin red y sin la cartografía del DANE."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapa_ejecutivo import AZULES, MapaEjecutivo, Rango, clasificar, por_cuantiles
from mapa_ejecutivo.mapa import _fmt
from mapa_ejecutivo.preparar import validar_coordenadas
from mapa_ejecutivo.validar import verificar


def _base(n=40, semilla=1):
    rng = np.random.default_rng(semilla)
    return pd.DataFrame({
        "cliente": [f"Cliente {i:03d}" for i in range(n)],
        "lat": 4.6 + rng.normal(0, 0.05, n),
        "lon": -74.1 + rng.normal(0, 0.05, n),
        "venta": rng.lognormal(np.log(3e6), 0.8, n).round(-3),
        "visitas": np.arange(n, dtype="int64") * 1000,
    })


# ── preparar ────────────────────────────────────────────────────────────────
def test_validar_coordenadas_detecta_cada_problema():
    df = _base(10)
    df.loc[0, ["lat", "lon"]] = [np.nan, np.nan]
    df.loc[1, ["lat", "lon"]] = [0.0, 0.0]
    df.loc[2, ["lat", "lon"]] = [df.loc[2, "lon"], df.loc[2, "lat"]]   # invertida
    df["lat"] = df["lat"].astype(object)
    df.loc[3, "lat"] = "4,65"                                           # coma decimal

    limpio, inf = validar_coordenadas(df, verbose=False)

    assert inf["filas"] == 10
    assert inf["sin_coordenada"] == 2          # NaN y el texto que no es número
    assert inf["en_cero"] == 1
    assert inf["posible_lat_lon_invertida"] == 1
    assert inf["utilizables"] == len(limpio) == 6
    assert limpio["lat"].dtype.kind == "f"


def test_cero_se_descarta_aunque_el_bbox_lo_contenga():
    df = pd.DataFrame({"lat": [0.0, 1.0], "lon": [0.0, 1.0]})
    bbox = dict(lat_min=-5, lat_max=5, lon_min=-5, lon_max=5)
    limpio, inf = validar_coordenadas(df, bbox=bbox, verbose=False)
    assert inf["en_cero"] == 1 and inf["utilizables"] == 1
    assert limpio["lat"].tolist() == [1.0]


def test_validar_coordenadas_columna_faltante():
    with pytest.raises(KeyError, match="latitud"):
        validar_coordenadas(pd.DataFrame({"lat": [1]}), "latitud", "lon", verbose=False)


# ── rangos ──────────────────────────────────────────────────────────────────
def test_cuartiles_reparten_y_clasifican_todo():
    v = pd.Series(np.arange(1, 101) * 1e5)
    rangos = por_cuantiles(v)
    assert [r.color for r in rangos] == AZULES
    assert rangos[0].desde == 0 and rangos[-1].hasta == float("inf")
    clase = clasificar(v, rangos)
    assert (clase >= 0).all()
    assert clase.value_counts().sort_index().tolist() == [25, 25, 25, 25]


def test_cuantiles_repetidos_no_producen_rangos_vacios():
    rangos = por_cuantiles([1e6] * 50 + [2e6, 3e6])
    cortes = [r.desde for r in rangos]
    assert cortes == sorted(set(cortes))
    assert all((clasificar([1e6] * 50 + [2e6, 3e6], rangos) == i).any()
               for i in range(len(rangos)))


def test_cuantiles_sin_datos_y_n_invalido():
    assert por_cuantiles([np.nan, -1, 0]) == []
    with pytest.raises(ValueError):
        por_cuantiles([1, 2, 3], n=5)          # 5 rangos y solo 4 colores
    with pytest.raises(ValueError):
        por_cuantiles([1, 2, 3], n=0)


def test_clasificar_nulos_y_negativos_son_sin_dato():
    rangos = [Rango("a", 0, 10, "#000000", 4), Rango("b", 10, float("inf"), "#ffffff", 6)]
    assert clasificar([np.nan, -3, 0, 9.99, 10, 1e9], rangos).tolist() == [-1, -1, 0, 0, 1, 1]


# ── formato ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("v, esperado", [
    (None, "—"), (float("nan"), "—"), (pd.NA, "—"), (pd.NaT, "—"),
    (np.int64(1234567), "1,234,567"), (np.float64(2.5), "2.5"), (7, "7"),
    (True, "True"), ("texto", "texto"),
])
def test_fmt(v, esperado):
    assert _fmt(v) == esperado


# ── mapa ────────────────────────────────────────────────────────────────────
def test_mapa_y_verificar_cuadran(tmp_path, capsys):
    df = _base()
    m = MapaEjecutivo(df, "lat", "lon", valor="venta", nombre="cliente", titulo="PRUEBA",
                      popup=[("Venta", "venta"), ("Visitas", "visitas")])
    ruta = m.guardar(tmp_path / "sub" / "mapa.html")
    assert ruta.exists()
    assert verificar(ruta, df, valor="venta", rangos=m.rangos, nombre="cliente")
    assert "0 fallos" in capsys.readouterr().out


def test_verificar_detecta_marcadores_que_faltan(tmp_path):
    df = _base()
    m = MapaEjecutivo(df.iloc[:-5], "lat", "lon", valor="venta", rangos=por_cuantiles(df.venta))
    ruta = m.guardar(tmp_path / "mapa.html")
    assert not verificar(ruta, df, valor="venta", rangos=m.rangos)


def test_verificar_no_se_confunde_con_color_de_marca_igual_a_un_rango(tmp_path):
    df = _base()
    m = MapaEjecutivo(df, "lat", "lon", valor="venta", nombre="cliente",
                      color_marca=AZULES[-1], agrupar_desde=10)
    ruta = m.guardar(tmp_path / "mapa.html")
    assert verificar(ruta, df, valor="venta", rangos=m.rangos, nombre="cliente")


def test_indice_filtrado_no_desalinea_las_filas(tmp_path):
    df = _base().iloc[::3]                      # índice salteado, como tras filtrar
    m = MapaEjecutivo(df, "lat", "lon", valor="venta", nombre="cliente")
    ruta = m.guardar(tmp_path / "mapa.html")
    assert verificar(ruta, df, valor="venta", rangos=m.rangos, nombre="cliente")


def test_textos_del_usuario_se_escapan(tmp_path):
    malos = ["<img src=x onerror=alert(1)>", "${alert(2)}", "a`b", "<script>alert(3)</script>"]
    df = _base(len(malos))
    df["cliente"] = malos
    df["nota"] = malos[::-1]
    m = MapaEjecutivo(df, "lat", "lon", valor="venta", nombre="cliente",
                      titulo="<b>titulo</b>", subtitulo="${sub}",
                      popup=[("<i>Nota</i>", "nota")])
    texto = m.guardar(tmp_path / "mapa.html").read_text(encoding="utf-8")
    for s in ["<img src=x", "${alert", "a`b", "<script>alert", "<b>titulo", "${sub}", "<i>Nota"]:
        assert s not in texto, s
    assert "&lt;img src=x onerror=alert(1)&gt;" in texto
    assert verificar(tmp_path / "mapa.html", df, valor="venta", rangos=m.rangos,
                     nombre="cliente")


@pytest.mark.parametrize("cambio, error", [
    (lambda d: d.drop(columns="venta"), KeyError),
    (lambda d: d.iloc[0:0], ValueError),
    (lambda d: d.assign(lat=[np.nan, *d.lat.tolist()[1:]]), ValueError),
    (lambda d: d.assign(lon=["x", *d.lon.tolist()[1:]]), ValueError),
    (lambda d: d.assign(lat=[95.0, *d.lat.tolist()[1:]]), ValueError),
])
def test_entradas_invalidas_dan_error_claro(cambio, error):
    with pytest.raises(error):
        MapaEjecutivo(cambio(_base()), "lat", "lon", valor="venta", nombre="cliente")


def test_popup_con_columna_inexistente():
    with pytest.raises(KeyError, match="no_existe"):
        MapaEjecutivo(_base(), "lat", "lon", popup=[("X", "no_existe")])


def test_color_no_hexadecimal_se_rechaza():
    with pytest.raises(ValueError):
        MapaEjecutivo(_base(), "lat", "lon", color_marca="red;background:url(x)")
    with pytest.raises(ValueError):
        MapaEjecutivo(_base(), "lat", "lon", valor="venta",
                      rangos=[Rango("a", 0, float("inf"), "azul", 4)])


def test_sin_valor_dibuja_sin_leyenda(tmp_path):
    df = _base(5)
    m = MapaEjecutivo(df, "lat", "lon", nombre="cliente")
    ruta = m.guardar(tmp_path / "mapa.html")
    assert verificar(ruta, df, nombre="cliente")
    assert "Total" not in ruta.read_text(encoding="utf-8")


def test_valores_nulos_salen_como_sin_dato(tmp_path):
    df = _base(12)
    df.loc[0, "venta"] = np.nan
    m = MapaEjecutivo(df, "lat", "lon", valor="venta", nombre="cliente")
    ruta = m.guardar(tmp_path / "mapa.html")
    texto = ruta.read_text(encoding="utf-8")
    assert "Sin dato" in texto
    assert verificar(ruta, df, valor="venta", rangos=m.rangos, nombre="cliente")


# ── capa territorial (solo si geopandas está instalado) ─────────────────────
def test_capa_departamentos_desde_shapefile(tmp_path):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Polygon

    cuadro = Polygon([(-74.5, 4.2), (-73.7, 4.2), (-73.7, 5.0), (-74.5, 5.0)])
    shp = tmp_path / "dptos.shp"
    gpd.GeoDataFrame({"nombre": ["Ficticio"]}, geometry=[cuadro], crs="EPSG:4326").to_file(shp)

    df = _base()
    m = MapaEjecutivo(df, "lat", "lon", valor="venta", nombre="cliente")
    m.capa_departamentos(shp)
    ruta = m.guardar(tmp_path / "mapa.html")
    texto = ruta.read_text(encoding="utf-8")
    assert "Ficticio" in texto and "Departamentos" in texto
    assert verificar(ruta, df, valor="venta", rangos=m.rangos, nombre="cliente")
    assert "DANE, Marco Geoestad" in texto      # folium lo serializa como JSON (\u00ed)


@pytest.mark.filterwarnings("ignore:.crs. was not provided")
def test_capa_sin_sistema_de_coordenadas_da_error_claro(tmp_path):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Point

    shp = tmp_path / "sin_crs.shp"
    gpd.GeoDataFrame({"n": [1]}, geometry=[Point(-74, 4)]).to_file(shp)
    m = MapaEjecutivo(_base(5), "lat", "lon")
    with pytest.raises(ValueError, match="sistema de coordenadas"):
        m.capa_departamentos(shp)


def test_sin_capas_no_atribuye_al_dane(tmp_path):
    texto = MapaEjecutivo(_base(5), "lat", "lon").guardar(tmp_path / "m.html").read_text(
        encoding="utf-8")
    assert "Esri" in texto and "DANE" not in texto

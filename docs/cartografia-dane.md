# Cartografía oficial de Colombia

El ejemplo corre sin cartografía. La capa territorial es opcional, pero un mapa
para comité casi siempre la necesita: sin contornos, un punto no dice en qué
departamento cae.

## De dónde se baja

El **Marco Geoestadístico Nacional (MGN)** del DANE, en su
[geoportal](https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/). Es la
fuente oficial: más actualizada y con los códigos correctos, que es lo que
permite cruzar por código y no por nombre.

Del paquete solo hacen falta dos capas:

| Capa | Para qué | Peso aproximado |
|---|---|---|
| `MGN_ADM_DPTO_POLITICO` | Contorno de departamentos | pocos MB |
| `MGN_ADM_MPIO_GRAFICO` | Municipios | decenas de MB |

El paquete completo pasa de 1 GB porque trae manzanas y sectores censales.
Para un mapa ejecutivo no se usan.

## Por qué no está en este repositorio

Porque pesa, porque se actualiza cada año y porque tiene su propia licencia.
Un repositorio de código no es sitio para 1,4 GB de geometría que el DANE ya
publica.

Si varios proyectos la comparten, guárdela **una sola vez** y enlácela desde
cada proyecto. Nunca la copie: cinco copias son cinco versiones distintas en
cuanto alguien actualice una.

## Simplificar no es opcional

La geometría del DANE sin simplificar produce HTML de **más de 40 MB**. Ese
archivo no se manda por correo, tarda en abrir y arrastra un detalle que a
escala nacional no se ve: el municipio se dibuja con miles de vértices y en
pantalla ocupa doce píxeles.

```python
m.capa_departamentos(shp, simplificar=0.005)   # nacional
m.capa_municipios(shp, simplificar=0.001)      # regional
```

Los valores están en grados. `0.005` ≈ 500 m: imperceptible a escala de país.
Un mapa nacional pasa de ~44 MB a ~3 MB sin diferencia visible.

Para un mapa regional, además recorte al área:

```python
m.capa_municipios(shp, bbox=(-76.8, 3.2, -75.9, 4.1))   # oeste, sur, este, norte
```

## Sistema de coordenadas

Las capas vienen en EPSG:4326 (latitud/longitud). La librería reproyecta por si
acaso, y si el shapefile no trae su `.prj` se niega a adivinar y da error. Si sus puntos están en coordenadas planas —MAGNA-SIRGAS, por ejemplo—,
conviértalos antes: mezclar sistemas pone Bogotá en el Atlántico.

## Comprobar antes de confiar

```python
from mapa_ejecutivo.preparar import validar_coordenadas
limpio, informe = validar_coordenadas(df, "lat", "lon")
```

Reporta cuántas filas no tienen coordenada, cuántas están en `(0, 0)` —que casi
nunca significa el Golfo de Guinea, sino "no sé dónde queda"— y cuántas parecen
traer **latitud y longitud invertidas**, que es el error más común y el más
fácil de no ver: los puntos aparecen en el mapa, solo que en otro continente.

## Atribución

El MGN es del DANE y se cita al usarlo. Al cargar una capa con
`capa_departamentos` o `capa_municipios`, el rótulo del mapa añade «Límites:
DANE, Marco Geoestadístico Nacional». Revise los términos de uso vigentes en el
geoportal antes de publicar un mapa.

# Reglas visuales

Por qué el mapa se ve así y no de otra forma. Cada regla viene de un mapa que
no se entendió en una reunión.

## 1 · Una escala de un solo tono para las magnitudes

De claro a oscuro dentro de la misma familia de color. Nada de rojo-amarillo-
verde para decir "cuánto vende".

Con una escala de un tono, el lector entiende el orden sin ir a la leyenda. Con
colores distintos tiene que consultarla en cada punto, y si el mapa se imprime
en gris o lo mira alguien que no distingue bien los tonos, se pierde entero.

Los colores distintos se reservan para lo que **no tiene orden**: una región, un
dueño, un canal.

## 2 · El tamaño acompaña al color

El punto crece con el rango. Refuerza la jerarquía sin meter una segunda
variable y salva la lectura cuando el color falla.

## 3 · Borde blanco de un píxel

En zona densa los puntos se solapan. Sin borde se funden en una mancha y no se
distingue si hay tres clientes o treinta.

## 4 · Los grandes se dibujan encima

Se pinta de menor a mayor rango. Si no, un cliente pequeño tapa al estratégico,
que es justo el que se fue a buscar al mapa.

## 5 · Cortes por cuantil, no a ojo

Cortar en números redondos elegidos pensando en los clientes grandes produce el
mapa entero del color más claro y tres puntos oscuros. Los cuartiles reparten y
el mapa comunica.

Si el negocio tiene cortes propios —los rangos comerciales ya pactados—, esos
mandan: se pasan explícitos y se documentan.

## 6 · Fondo gris claro

El fondo aporta contexto, no protagonismo. Un fondo satelital o de calles a todo
color compite con los datos.

> El fondo habitual para esto era CartoDB Positron. **Pasó a exigir clave de
> API:** sin ella devuelve teselas estampadas con "API KEY REQUIRED" sobre todo
> el mapa, y no produce ningún error en la consola del navegador. Se descubre
> mirando una captura. Esta librería usa el gris claro de Esri, que no pide
> clave.

## 7 · Una sola semántica por nivel

Si el color del punto significa venta, no puede significar también región en
otra capa. Dos escalas de color en el mismo mapa equivalen a ninguna.

Es la razón de que los racimos vayan en el tono de la marca y no en el
verde-amarillo-rojo que traen por defecto: esos colores codifican *cuántos* y
compiten con la leyenda, que codifica *cuánto*.

## 8 · La leyenda lleva conteos

No solo el color y su etiqueta: **cuántos puntos hay en cada rango y el total**.
Es la primera pregunta de cualquiera que abre el mapa, y ahorra la ronda de
"¿y cuántos son los estratégicos?".

## 9 · Mirar el mapa antes de mandarlo

Los conteos pueden cuadrar y el mapa estar mal: la leyenda tapando una ciudad,
un rótulo cortado, un color que en pantalla no se distingue del vecino. Eso solo
se ve abriéndolo. `ejemplo/qa_visual.py` automatiza la parte mecánica —que abra,
que pinte, que no tenga errores— y deja las capturas. Mirarlas es el paso que no
se puede delegar.

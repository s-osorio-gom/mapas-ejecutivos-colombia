"""Mapas ejecutivos en un solo archivo HTML, sobre cartografía oficial."""
from .mapa import COLOMBIA, MapaEjecutivo
from .rangos import AZULES, GRISES, VERDES, Rango, clasificar, por_cuantiles

__all__ = ["AZULES", "COLOMBIA", "GRISES", "VERDES", "MapaEjecutivo", "Rango",
           "clasificar", "por_cuantiles"]
__version__ = "1.0.0"

"""
Figura de Plotly con cuadros de animación que no pasan por su validación interna.

Plotly revisa cada propiedad de cada traza al construir una figura. Para una figura
normal eso es imperceptible, pero una animación con cien cuadros y nueve trazas por
cuadro son miles de objetos: construir el viaje del fotón tomaba un segundo y la
celda tridimensional cerca de tres, casi todo en esa revisión y nada en la física.

Los cuadros de estas animaciones salen de funciones propias con estructura fija, así
que la revisión no aporta nada. Esta figura construye datos y diseño sin validar, y
guarda los cuadros como diccionarios que solo se agregan al serializarla, que es el
único momento en que Streamlit los necesita.
"""

import plotly.graph_objects as go


class FiguraAnimada(go.Figure):

    def __init__(self, data=None, layout=None, cuadros=None):
        super().__init__(data=data, layout=layout, _validate=False)
        self._cuadros = list(cuadros or [])

    def to_dict(self):
        d = super().to_dict()
        if self._cuadros:
            d["frames"] = self._cuadros
        return d

    @classmethod
    def desde_diccionario(cls, d):
        return cls(data=d.get("data"), layout=d.get("layout"), cuadros=d.get("frames"))

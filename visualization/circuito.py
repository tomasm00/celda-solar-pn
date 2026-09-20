"""
El circuito equivalente de un diodo, con las corrientes del punto elegido.

Es el dibujo de la ecuación que resuelve la pestaña: la luz inyecta una corriente,
el diodo y la resistencia paralela se llevan una parte, y lo que sobra sale por la
resistencia serie hacia los terminales. Todas las cifras salen del modelo; el
dibujo no calcula nada.
"""


def _num(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def diagrama_html(v, j_salida, j_luz, j_diodo, j_paralelo, rs, v_juntura):
    """
    Circuito con las cuatro corrientes y los dos voltajes del punto elegido.

    Corrientes en mA/cm², voltajes en V. `v` es el voltaje en los terminales y
    `v_juntura` el que realmente ve la juntura, que es mayor en la caída sobre la
    resistencia serie: ahí está la ecuación implícita.
    """
    caida = v_juntura - v
    ramas = [
        (120, "luz", f"{_num(1e3 * j_luz)} mA/cm²", "#E5A33F", "lo que genera la celda"),
        (300, "diodo", f"{_num(1e3 * j_diodo)} mA/cm²", "#E4664A", "se recombina dentro"),
        (470, "R paralelo", f"{_num(1e3 * j_paralelo, 3)} mA/cm²", "#8894A8", "fuga por los bordes"),
    ]
    etiquetas = "".join(
        f'<text x="{x}" y="196" class="ci-t" text-anchor="middle">{nombre}</text>'
        f'<text x="{x}" y="214" class="ci-v" text-anchor="middle" fill="{color}">{valor}</text>'
        f'<text x="{x}" y="231" class="ci-s" text-anchor="middle">{nota}</text>'
        for x, nombre, valor, color, nota in ramas)

    return f"""    <style>
      .ci-marco {{border:1px solid #2A3542; border-radius:8px; background:#131B26; padding:10px 12px 6px;
                  overflow-x:auto;}}
      .ci-marco svg {{display:block; min-width:640px; width:100%; height:auto;}}
      .ci-cable {{stroke:#8494A6; stroke-width:1.6; fill:none;}}
      .ci-pieza {{stroke:#C7D2DE; stroke-width:1.8; fill:none;}}
      .ci-t {{fill:#C7D2DE; font-family:ui-monospace,Consolas,monospace; font-size:12.5px;}}
      .ci-v {{font-family:ui-monospace,Consolas,monospace; font-size:14px; font-weight:600;}}
      .ci-s {{fill:#7C8C96; font-family:system-ui,sans-serif; font-size:11.5px;}}
    </style>
    <div class="ci-marco">
      <svg viewBox="0 0 760 250" role="img"
           aria-label="Circuito equivalente con la corriente de luz, el diodo, la resistencia paralela y la resistencia serie">
        <defs>
          <marker id="ci-flecha" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 z" fill="#8494A6"/>
          </marker>
        </defs>
        <path class="ci-cable" d="M120 60 H560"/>
        <path class="ci-cable" d="M120 170 H560"/>
        <path class="ci-cable" d="M120 60 V100 M120 140 V170"/>
        <path class="ci-cable" d="M300 60 V96 M300 144 V170"/>
        <path class="ci-cable" d="M470 60 V100 M470 140 V170"/>
        <circle class="ci-pieza" cx="120" cy="120" r="20"/>
        <path class="ci-cable" d="M120 134 V106" marker-end="url(#ci-flecha)"/>
        <path class="ci-pieza" d="M282 144 L318 144 L300 116 Z"/>
        <path class="ci-pieza" d="M282 116 H318"/>
        <rect class="ci-pieza" x="456" y="100" width="28" height="40" rx="3"/>
        <rect class="ci-pieza" x="586" y="46" width="52" height="28" rx="3"/>
        <path class="ci-cable" d="M560 60 H586 M638 60 H690 V110"/>
        <path class="ci-cable" d="M560 170 H690 V138"/>
        <path class="ci-cable" d="M672 110 H708 M672 138 H708"/>
        <text x="612" y="36" class="ci-t" text-anchor="middle">R serie</text>
        <text x="612" y="92" class="ci-v" text-anchor="middle" fill="#C98A1B">−{_num(1e3 * caida)} mV</text>
        <path class="ci-cable" d="M520 60 H556" marker-end="url(#ci-flecha)"/>
        <text x="538" y="46" class="ci-v" text-anchor="middle" fill="#5FC49B">{_num(1e3 * j_salida)}</text>
        <text x="538" y="88" class="ci-s" text-anchor="middle">sale al circuito</text>
        <text x="724" y="118" class="ci-t" text-anchor="middle">{_num(v, 3)} V</text>
        <text x="724" y="146" class="ci-s" text-anchor="middle">terminales</text>
        <text x="392" y="120" class="ci-t" text-anchor="middle">la juntura ve</text>
        <text x="392" y="140" class="ci-v" text-anchor="middle" fill="#C7D2DE">{_num(v_juntura, 3)} V</text>
        {etiquetas}
      </svg>
    </div>
    """

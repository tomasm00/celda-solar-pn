"""
Diagrama del recorrido de la luz hasta la corriente, con las cifras de la celda.

Sigue la secuencia con que la Unidad 3 (lámina 17) describe la operación de una
celda solar —absorción, supervivencia a la recombinación, separación en la juntura
y colección en los contactos—, precedida de las dos pérdidas ópticas de la
superficie que describe la Unidad 2 (lámina 32). Cada paso lleva el número que lo
resume en la celda actual, calculado por el modelo; el diagrama no contiene
ninguna cifra escrita a mano.
"""

import html

from physics.collection import CLAVES_COLECTADAS


def _pct(x):
    return f"{100 * x:.1f}".replace(".", ",") + " %"


def _num(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def pasos_del_recorrido(fracciones, fraccion_sombra, j_maxima_ma=None, modo="espectro",
                        lambda_nm=None, reparto_mecanismos=None):
    """
    Arma los seis pasos con sus cifras.

    `fracciones` son los diez destinos, referidos a los fotones que llegan a la
    superficie de silicio. Aquí se refieren a todos los que llegan a la celda,
    incluida la parte tapada por la malla, porque ése es el orden físico: la luz
    choca primero con los dedos de plata.
    """
    k = 1.0 - fraccion_sombra
    f = {c: k * v for c, v in fracciones.items()}

    reflejados = f["reflejados"]
    dejan_celda = f["aluminio"] + f["escapan"]
    entran = k - reflejados
    absorbidos = entran - dejan_celda
    rec_superficie = f["emisor_superficie"] + f["base_superficie"]
    rec_volumen = f["emisor_volumen"] + f["base_volumen"]
    colectados = sum(f[c] for c in CLAVES_COLECTADAS)

    de_cada = ("de cada 100 fotones que llegan del Sol" if modo == "espectro"
               else f"de cada 100 fotones de {lambda_nm:.0f} nm que llegan")

    if modo == "espectro" and j_maxima_ma is not None:
        cifra_luz, unidad_luz = _num(j_maxima_ma, 1), "mA/cm² posibles"
        texto_luz = ("Si cada fotón entre 300 y 1200 nm se convirtiera en una carga, la "
                     "celda entregaría esta corriente. Es el techo contra el que se mide todo.")
        cifra_par, unidad_par = _num(j_maxima_ma * absorbidos, 1), "mA/cm² en pares"
        cifra_final, unidad_final = _num(j_maxima_ma * colectados, 2), "mA/cm² de corriente"
    else:
        cifra_luz, unidad_luz = "100", "fotones"
        texto_luz = (f"Todos del mismo color. Cada uno lleva {_num(1240 / lambda_nm)} eV "
                     f"de energía.")
        cifra_par, unidad_par = _pct(absorbidos), "crean un par"
        cifra_final, unidad_final = _pct(colectados), "producen corriente"

    if reparto_mecanismos:
        mecanismos = ("En el volumen de la base: "
                      + " · ".join(f"{m} {_pct(v)}" for m, v in reparto_mecanismos.items()))
    else:
        mecanismos = "En el volumen compiten tres mecanismos: SRH, Auger y radiativo."

    return [
        dict(titulo="Llega la luz", cifra=cifra_luz, unidad=unidad_luz, texto=texto_luz,
             perdida=f"{_pct(fraccion_sombra)} choca con la malla de plata"),
        dict(titulo="Cruza la superficie", cifra=_pct(entran), unidad="entra al silicio",
             texto="La interfaz entre el aire y el silicio devuelve una parte de la luz, "
                   "más en el azul que en el rojo.",
             perdida=f"{_pct(reflejados)} se refleja"),
        dict(titulo="Se absorbe según su color", cifra=_pct(absorbidos),
             unidad="se absorbe",
             texto="El azul se agota en las primeras décimas de micra; el infrarrojo "
                   "puede cruzar la celda entera.",
             perdida=(f"{_pct(dejan_celda)} llega al fondo sin absorberse"
                      if dejan_celda > 5e-4 else None)),
        dict(titulo="Nace un par electrón-hueco", cifra=cifra_par, unidad=unidad_par,
             texto="Cada fotón absorbido sube un electrón a la banda de conducción y deja "
                   "un hueco en su lugar.",
             perdida=None),
        dict(titulo="Compite con la recombinación", cifra=_pct(rec_superficie + rec_volumen),
             unidad="se recombina", tono="perdida",
             texto="El par difunde al azar. Si antes de llegar a la juntura encuentra una "
                   "superficie o un defecto, se recombina. " + mecanismos + ".",
             perdida=(f"{_pct(rec_superficie)} en una superficie · "
                      f"{_pct(rec_volumen)} en el volumen")),
        dict(titulo="La juntura lo separa", cifra=cifra_final, unidad=unidad_final,
             texto="El campo eléctrico de la juntura p-n empuja el electrón al emisor y el "
                   "hueco a la base. Los contactos lo entregan al circuito.",
             perdida=None, final=True,
             nota=f"{_pct(colectados)} {de_cada}"),
    ], de_cada


def pasos_de_la_curva(curva, ff0, j_l_desnuda, fraccion_sombra, j0, eg_v, soles):
    """
    Los seis pasos del ensayo eléctrico, de la corriente de la luz a la potencia.

    Sigue el orden en que la Unidad 4 lee una curva I-V: primero cuánta corriente
    hay, después hasta qué voltaje se puede cargar la celda, después dónde conviene
    trabajarla, y al final cuánta potencia queda. Cada tarjeta lleva la pérdida que
    explica el paso siguiente.
    """
    j_con_malla = j_l_desnuda * (1.0 - fraccion_sombra)
    deficit = eg_v - curva.v_oc
    return [
        dict(titulo="La luz, ya convertida en corriente", cifra=_num(1e3 * j_l_desnuda),
             unidad="mA/cm² fotogenerados",
             texto="Es la corriente que calcularon las Pestañas 1 y 2: la eficiencia cuántica "
                   "integrada con el espectro solar.",
             perdida=f"{_pct(fraccion_sombra)} lo tapa la malla de plata"),
        dict(titulo="En cortocircuito", cifra=_num(1e3 * curva.j_sc), unidad="mA/cm²",
             texto="Con los terminales unidos no hay voltaje que haga conducir al diodo, así que "
                   "sale casi toda la corriente que quedó.",
             perdida=f"{_num(1e3 * (j_con_malla - curva.j_sc), 3)} mA/cm² se van por la fuga y "
                     f"las resistencias"),
        dict(titulo="El voltaje que sostiene", cifra=_num(curva.v_oc, 4),
             unidad="V en circuito abierto",
             texto="Sin corriente que salga, la celda se carga hasta que la recombinación en "
                   "oscuridad se come todo lo que genera la luz.",
             perdida=f"queda {_num(deficit, 3)} V bajo la banda prohibida, {_num(eg_v, 3)} V",
             tono="perdida"),
        dict(titulo="El punto de trabajo", cifra=_num(curva.v_mpp, 3),
             unidad=f"V × {_num(1e3 * curva.j_mpp)} mA/cm²",
             texto="El voltaje donde el producto de corriente por voltaje es máximo. Es donde "
                   "conviene operar la celda.", perdida=None),
        dict(titulo="El factor de forma", cifra=_num(curva.ff, 4),
             unidad=f"de {_num(ff0, 4)} ideal",
             texto="Mide cuán cuadrada es la curva: la potencia máxima dividida por el producto "
                   "del voltaje y la corriente extremos.",
             perdida=f"{_num(ff0 - curva.ff, 4)} se los llevan la resistencia serie y la fuga"),
        dict(titulo="La potencia que entrega", cifra=_num(1e3 * curva.p_max),
             unidad=f"mW/cm² · {_num(100 * curva.eficiencia)} % de eficiencia",
             texto="La potencia del punto de trabajo, dividida por la que trae el sol, es la "
                   "eficiencia de la celda.", perdida=None, final=True,
             nota=f"el sol entrega {_num(100 * soles, 1)} mW/cm², {_num(soles, 2)} soles"),
    ]


def diagrama_html(pasos, de_cada):
    """Tarjetas conectadas por flechas. Se reordenan solas en pantallas angostas."""
    tarjetas = []
    for i, p in enumerate(pasos, start=1):
        final = p.get("final", False)
        borde = "#5FC49B" if final else "#2A3542"
        fondo = "rgba(95,196,155,0.10)" if final else "#131B26"
        color_cifra = ("#5FC49B" if final else
                       "#E58063" if p.get("tono") == "perdida" else "#E8ECF2")
        perdida = (f"<div class='fl-perdida'>↳ {html.escape(p['perdida'])}</div>"
                   if p.get("perdida") else "<div class='fl-perdida fl-vacia'></div>")
        nota = (f"<div class='fl-nota'>{html.escape(p['nota'])}</div>" if p.get("nota") else "")
        tarjetas.append(f"""
          <div class="fl-paso" style="border-color:{borde}; background:{fondo};">
            <div class="fl-num">{i}</div>
            <div class="fl-titulo">{html.escape(p['titulo'])}</div>
            <div class="fl-cifra" style="color:{color_cifra};">{html.escape(p['cifra'])}
              <span class="fl-unidad">{html.escape(p['unidad'])}</span></div>
            <div class="fl-texto">{html.escape(p['texto'])}</div>
            {perdida}{nota}
          </div>""")

    return f"""
    <style>
      .fl-marco {{display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:10px;
                  margin:6px 0 4px;}}
      @media (max-width: 1100px) {{ .fl-marco {{grid-template-columns:repeat(3, minmax(0,1fr));}} }}
      @media (max-width: 640px)  {{ .fl-marco {{grid-template-columns:repeat(2, minmax(0,1fr));}} }}
      .fl-paso {{position:relative; border:1px solid; border-radius:8px; padding:11px 12px 10px;
                 display:flex; flex-direction:column; gap:4px; min-width:0;}}
      .fl-paso:not(:last-child)::after {{content:"→"; position:absolute; right:-11px; top:14px;
                 color:#E5A33F; font-size:15px; font-weight:700;}}
      .fl-num {{font-size:0.68rem; letter-spacing:0.08em; color:#8894A8;}}
      .fl-titulo {{font-size:0.9rem; font-weight:600; color:#E8ECF2; line-height:1.25;}}
      .fl-cifra {{font-size:1.28rem; font-weight:600; font-variant-numeric:tabular-nums;
                  line-height:1.2; margin-top:2px;}}
      .fl-unidad {{font-size:0.74rem; font-weight:400; color:#8894A8; margin-left:2px;}}
      .fl-texto {{font-size:0.78rem; color:#BAC4D2; line-height:1.45;}}
      .fl-perdida {{font-size:0.76rem; color:#E58063; line-height:1.35; margin-top:auto;
                    padding-top:4px;}}
      .fl-nota {{font-size:0.74rem; color:#8894A8; line-height:1.35;}}
      .fl-pie {{font-size:0.78rem; color:#8894A8; margin:2px 0 0;}}
    </style>
    <div class="fl-marco">{''.join(tarjetas)}</div>
    <div class="fl-pie">Porcentajes {html.escape(de_cada)}. Todas las cifras salen del modelo
    con los valores actuales de la barra lateral.</div>
    """

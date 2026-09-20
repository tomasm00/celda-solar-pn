"""Pestaña 1 - De la luz a la corriente: absorción, generación y destino de los pares."""

import numpy as np
import pandas as pd
import streamlit as st

import config
from physics.collection import (
    CLAVES_COLECTADAS,
    CLAVES_OPTICAS,
    reparto_por_destino,
    transporte as armar_transporte,
)
from physics.front_grid import malla
from physics.material import juntura as resolver_juntura, reparto_por_mecanismo
from physics.optics import campo_optico
from physics.quantum_efficiency import destinos_de_celda, generar_sectores
from units import celsius_a_kelvin, cm_a_um, um_a_cm
from validation.monitor import EN_ORDEN, vigilar_absorcion
from visualization import cell3d, flujo, optics_plots, viaje_foton
from visualization.figura_animada import FiguraAnimada

NODOS_EN_DEPLECION = 12


@st.cache_data(show_spinner=False, max_entries=10)
def _resolver(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia, mu_p, tau_p_us,
              mu_n, tau_n_us, s_f, s_r, dispersion, r_fija, n_dedos, ancho_dedo_um):
    """
    Resuelve LA celda en el orden en que las piezas dependen entre sí.

    La juntura va primero porque sus bordes entran como nodos forzados de la grilla.
    Las probabilidades de destino son las promediadas por área sobre los sectores,
    las mismas que usan las Pestañas 2, 3 y 4, para que las cuatro describan la misma
    celda (D-28). Con dispersión cero coinciden exactamente con las de la celda
    homogénea.
    """
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    W = d_n + W_p
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLECION),
                         reflectancia_fija=r_fija)
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    sectores = generar_sectores(config.N_SECTORES, tau_n_us * 1e-6, s_f, dispersion)
    destinos = destinos_de_celda(campo, union, W, tr, sectores)
    reparto = reparto_por_destino(campo, destinos, union)
    grid = malla(n_dedos, ancho_dedo_um * 1e-4)
    return campo, union, tr, destinos, reparto, grid


@st.cache_data(show_spinner=False, max_entries=6)
def _figura_3d(_campo, _union, _destinos, huella, fraccion_sombra, d_n_um, W_um, modo,
               lambda_nm, irradiancia, vista_um, exagerar, trayectorias, semilla):
    """
    La animación se guarda como diccionario: así la caché no vuelve a construir los
    cuadros cada vez que la lee. `huella` reúne los parámetros físicos que entran por
    los argumentos con guion bajo, que Streamlit excluye de la clave (D-22).
    """
    fig, tanda = cell3d.figura_celda_3d(
        _campo, _union, _destinos, fraccion_sombra, d_n_um, W_um, modo=modo,
        lambda_nm=lambda_nm, irradiancia=irradiancia, profundidad_vista_um=vista_um,
        exagerar_deplecion=exagerar, mostrar_trayectorias=trayectorias, semilla=semilla)
    return fig.to_dict(), tanda


@st.cache_data(show_spinner=False, max_entries=12)
def _figura_viaje(_campo, _union, _tr, _destinos, huella, fraccion_sombra, t_k, j_ma, modo,
                  lambda_nm, semilla, forzar, _mecanismos):
    fig, ficha = viaje_foton.viaje_de_un_foton(
        _campo, _union, _tr, _destinos, fraccion_sombra, t_k, j_ma, modo=modo,
        lambda_nm=lambda_nm, semilla=semilla, forzar=forzar, mecanismos=_mecanismos)
    return fig.to_dict(), ficha


def _parametros(s, **cambios):
    base = dict(d_n_um=s.d_n_um, W_p_um=s.W_p_um, na=s.NA, nd=s.ND, t_c=s.T_c,
                reflector=s.reflector_trasero, irradiancia=s.irradiancia_soles,
                mu_p=s.mu_p, tau_p_us=s.tau_p_us, mu_n=s.mu_n, tau_n_us=s.tau_n_us,
                s_f=s.S_f, s_r=s.S_r, dispersion=s.dispersion_sectores,
                r_fija=config.reflectancia_fija_de(s), n_dedos=s.n_dedos,
                ancho_dedo_um=s.ancho_dedo_um)
    base.update(cambios)
    return base


def _pct(x, dec=1):
    return f"{100 * x:.{dec}f}".replace(".", ",") + " %"


def _prof(um):
    return optics_plots._profundidad_texto(um)


def render():
    s = st.session_state
    modo = s.modo_iluminacion
    campo, union, tr, destinos, reparto, grid = _resolver(**_parametros(s))
    W_um = s.d_n_um + s.W_p_um
    fs = grid.fraccion_sombra
    i_lam = int(np.argmin(np.abs(campo.lambda_nm - s.lambda_nm)))
    lam = float(campo.lambda_nm[i_lam])
    fr = reparto.integrado if modo == "espectro" else reparto.en_color(i_lam)
    j_celda = reparto.j_sc * (1.0 - fs)

    st.session_state["_bus"]["absorcion"] = dict(
        campo=campo, union=union, tr=tr, destinos=destinos, reparto=reparto,
        tau_n_s=s.tau_n_us * 1e-6, tau_p_s=s.tau_p_us * 1e-6, NA=s.NA, ND=s.ND,
        j_fotogenerada=j_celda)

    mecanismos = {"emisor": reparto_por_mecanismo(s.tau_p_us * 1e-6, s.ND),
                  "base": reparto_por_mecanismo(s.tau_n_us * 1e-6, s.NA)}

    # ------------------------------------------------------------------ portada
    st.subheader("De la luz a la corriente")
    st.write(
        "Esta pestaña sigue a la luz desde que llega a la celda hasta que se convierte en "
        "corriente eléctrica. En el camino hay cuatro momentos que deciden cuánto se "
        "aprovecha: cuánta luz logra entrar al silicio, a qué profundidad se absorbe cada "
        "color, cuántos de los pares electrón-hueco creados sobreviven a la recombinación, "
        "y cuántos alcanzan la juntura p-n, la única parte de la celda capaz de separarlos y "
        "enviarlos al circuito. El diagrama resume ese recorrido con los valores de la celda "
        "actual; cada sección de más abajo examina uno de sus pasos."
    )
    if modo == "color":
        st.caption(f"Modo de un solo color: todas las cifras corresponden a luz de **{lam:.0f} nm**. "
                   f"Se cambia en la barra lateral, en «Luz y óptica».")

    pasos, de_cada = flujo.pasos_del_recorrido(
        fr, fs, j_maxima_ma=1e3 * reparto.j_maxima if modo == "espectro" else None,
        modo=modo, lambda_nm=lam, reparto_mecanismos=mecanismos["base"])
    st.markdown(flujo.diagrama_html(pasos, de_cada), unsafe_allow_html=True)

    st.caption(
        f"Parámetros que gobiernan este recorrido: zona de depleción de "
        f"**{_prof(cm_a_um(union.W_dep))}** con un potencial de contacto de "
        f"{optics_plots._coma(union.psi0, 3)} V · longitud de difusión de **{_prof(cm_a_um(tr.L_p))}** en el emisor "
        f"y **{_prof(cm_a_um(tr.L_n))}** en la base · cociente S·L/D de "
        f"**{optics_plots._coma(tr.peso_superficie_frontal, 1)}** en la cara frontal y "
        f"**{optics_plots._coma(tr.peso_superficie_trasera, 2)}** en la trasera. Ese cociente compara la rapidez "
        f"con que una superficie captura portadores contra la rapidez con que el material los "
        f"hace difundir: por encima de 1, la superficie gana."
    )

    avisos = [v for v in vigilar_absorcion(st.session_state["_bus"]["absorcion"])
              if v.estado != EN_ORDEN]
    for v in avisos:
        st.warning(f"**Monitor físico · {v.nombre}.** {v.mensaje}", icon="⚠")

    # ------------------------------------------------------------ celda 3D
    st.divider()
    st.markdown("### La celda bajo la luz")
    st.write(
        "Cada punto es un fotón individual. Su color, el lugar donde cae, si rebota, a qué "
        "profundidad se absorbe y qué le ocurre al par que crea se sortean uno por uno con las "
        "mismas probabilidades que calculan las cifras de esta pestaña. Con suficientes fotones, "
        "los conteos de la animación convergen a los del modelo, y la tabla de abajo lo compara."
    )
    prof90 = float(cm_a_um(np.log(10.0) / campo.alpha[i_lam]))
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        acercar = st.toggle("Acercar al emisor",
                            value=(modo == "color" and prof90 < 0.8 * s.d_n_um),
                            help="Muestra solo los primeros micrones, donde se absorbe la luz azul.")
    with c2:
        exagerar = st.toggle("Ampliar la zona de depleción", value=False,
                             help=f"Solo visual. Su ancho real es {_prof(cm_a_um(union.W_dep))}.")
    with c3:
        trayectorias = st.toggle("Mostrar trayectorias", value=True,
                                 help="Dibuja el camino de cada fotón, con sus rebotes en el "
                                      "aluminio, y la línea que une cada par con su destino.")
    with c4:
        s.setdefault("tanda_3d", 7)
        if st.button("Nueva tanda de fotones", use_container_width=True):
            s.tanda_3d += 1

    huella = tuple(_parametros(s).values())
    dict3d, tanda = _figura_3d(
        campo, union, destinos, huella, fs, s.d_n_um, W_um, modo, lam, s.irradiancia_soles,
        s.d_n_um * 1.6 if acercar else W_um, exagerar, trayectorias, s.tanda_3d)
    st.plotly_chart(FiguraAnimada.desde_diccionario(dict3d), use_container_width=True)
    st.caption(
        f"Se lanzan **{tanda.n} fotones**, en proporción a los "
        f"{optics_plots._coma(s.irradiancia_soles)} soles de irradiancia. Los dedos de plata "
        f"ocupan la fracción real del área que tapa la malla. Cada par queda marcado **donde "
        f"nació**, con el color de su destino: rombo verde si llegó a la juntura y produjo "
        f"corriente, cruz roja si murió en una superficie, cruz rosada si se recombinó en el "
        f"volumen. La línea que sale de cada marca apunta a dónde terminó: al plano de la "
        f"juntura o a la superficie más cercana. Es solo el destino; el camino real del portador "
        f"es una difusión al azar. Con el reflector encendido, los fotones que llegan al fondo "
        f"rebotan en el aluminio y su trayectoria dibuja una V. La figura se puede girar y "
        f"acercar con el ratón."
    )
    with st.expander("¿Por qué casi no hay cruces rosadas en el medio de la base?"):
        def _en_volumen(reparto_ej):
            r_ = reparto_ej.integrado
            absorbidos = sum(v for k, v in r_.items() if k not in CLAVES_OPTICAS)
            return (r_["emisor_volumen"] + r_["base_volumen"]) / max(absorbidos, 1e-30)

        ejemplos = []
        for tau_ej in (1.0, 0.1):
            resultado = _resolver(**_parametros(s, tau_n_us=tau_ej))
            ejemplos.append((tau_ej, float(cm_a_um(resultado[2].L_n)), _en_volumen(resultado[4])))
        (t1, L1, v1), (t2, L2, v2) = ejemplos

        st.markdown(
            f"Porque en esta celda casi ningún par se recombina en el volumen, y no es un "
            f"error: hoy lo hacen **{_pct(_en_volumen(reparto))}** de los pares. Un par que nace "
            f"en la base recorre en promedio **{_prof(cm_a_um(tr.L_n))}** antes de recombinarse, "
            f"y la base mide **{s.W_p_um:.0f} µm**: si la longitud de difusión es mayor que la "
            f"base, al par le sobra distancia para alcanzar la juntura o la cara trasera. En el "
            f"emisor manda la superficie frontal, que con {s.S_f:.0e} cm/s captura los pares "
            f"antes de que el volumen alcance a recombinarlos. Por eso los rombos verdes aparecen "
            f"a lo largo de toda la base, pero las cruces rosadas son raras."
        )
        st.markdown(
            f"Para verlas, baja el tiempo de vida de la base, τₙ. Con {optics_plots._coma(t1, 1)} µs "
            f"la longitud de difusión cae a {_prof(L1)} y se recombinan en el volumen "
            f"{_pct(v1)} de los pares; con {optics_plots._coma(t2, 1)} µs cae a {_prof(L2)} y son "
            f"{_pct(v2)}, casi todos nacidos en el interior de la base."
        )
        st.markdown(
            "Hay un matiz, que es una limitación declarada del modelo: la vida media del emisor "
            "se usa tal como se elige, sin agregarle la recombinación de Auger. Con el dopaje "
            "asignado, Auger limitaría esa vida a menos de un nanosegundo y el volumen del emisor "
            "recombinaría casi todos sus pares; el modelo, en cambio, deja que muchos lleguen a la "
            "juntura. El aviso del monitor lo señala."
        )

    izq, der = st.columns([3, 2], gap="large")
    with izq:
        st.markdown("#### Qué le pasa a esta luz")
        k = 1.0 - fs
        filas = [("malla", "Chocan con la malla de plata", fs)]
        filas += [(c, et, k * fr[c]) for c, et in (
            ("reflejados", "Se reflejan en la superficie"),
            ("emisor_colectados", "Emisor · llegan a la juntura"),
            ("emisor_superficie", "Emisor · mueren en la superficie frontal"),
            ("emisor_volumen", "Emisor · se recombinan en el volumen"),
            ("deplecion", "Zona de depleción · se separan de inmediato"),
            ("base_colectados", "Base · llegan a la juntura"),
            ("base_volumen", "Base · se recombinan en el volumen"),
            ("base_superficie", "Base · mueren en la cara trasera"),
            ("aluminio", "Llegan al fondo y los absorbe el aluminio"),
            ("escapan", "Rebotan en el aluminio y escapan por el frente"),
        )]
        if not campo.reflector:
            filas = [f for f in filas if f[0] != "escapan"]
        n = max(tanda.n, 1)
        tabla = pd.DataFrame({
            "Destino": [et for _, et, _ in filas] + ["Total que produce corriente"],
            "Modelo": [_pct(v, 2) for _, _, v in filas]
                      + [_pct(k * sum(fr[c] for c in CLAVES_COLECTADAS), 2)],
            "En esta tanda": [f"{tanda.cuentas[c]} de {n}" for c, _, _ in filas]
                             + [f"{sum(tanda.cuentas[c] for c in CLAVES_COLECTADAS)} de {n}"],
        })
        st.dataframe(tabla, hide_index=True, use_container_width=True, height=458)
        st.caption(
            "«Modelo» es la probabilidad exacta, calculada integrando la generación y las "
            "probabilidades de destino sobre toda la profundidad" +
            (" y todo el espectro solar" if modo == "espectro" else "") +
            ". «En esta tanda» cuenta los fotones sorteados arriba: con pocos fotones difieren "
            "por azar, igual que en una medición con pocos eventos."
        )

    with der:
        otro = _resolver(**_parametros(s, reflector=not s.reflector_trasero))
        reparto_otro, grid_otro = otro[4], otro[5]
        if modo == "color":
            st.markdown(f"#### El color de {lam:.0f} nm")
            m1, m2 = st.columns(2)
            m1.metric("63 % absorbido a", _prof(float(cm_a_um(1.0 / campo.alpha[i_lam]))),
                      help="Profundidad 1/α: donde el flujo cae al 37 % del que entró.")
            m2.metric("90 % absorbido a", _prof(prof90))
            llega_fondo = float((1.0 - campo.R[i_lam]) * np.exp(-campo.alpha[i_lam] * campo.W_cm))
            eqe_aqui = sum(fr[c] for c in CLAVES_COLECTADAS)
            eqe_otro = sum(reparto_otro.en_color(i_lam)[c] for c in CLAVES_COLECTADAS)
            if prof90 < s.d_n_um:
                st.info(
                    f"Este color se absorbe casi entero dentro del emisor, a menos de "
                    f"{_prof(prof90)} de la superficie. Ahí manda la cara frontal: con una "
                    f"velocidad de recombinación de {s.S_f:.0e} cm/s, la mayoría de estos pares "
                    f"muere en la superficie antes de alcanzar la juntura.")
            elif llega_fondo > 0.01:
                st.info(
                    f"El {_pct(llega_fondo)} de los fotones de este color que llega a la celda "
                    f"cruza los {W_um:.0f} µm sin absorberse. Para este color la celda es "
                    f"demasiado delgada.")
            else:
                st.info("Este color se absorbe principalmente en la base, donde la longitud de "
                        "difusión es larga y la mayoría de los pares alcanza la juntura.")
            if llega_fondo < 1e-3:
                st.caption(
                    f"**Sobre el reflector trasero.** A {lam:.0f} nm prácticamente ningún fotón "
                    f"llega al fondo: el 90 % ya se absorbió a {_prof(prof90)}. Por eso activar el "
                    f"reflector no cambia nada para este color. Su efecto aparece desde el rojo "
                    f"lejano hacia el infrarrojo, por encima de unos 900 nm.")
            else:
                estado_ref = "encendido" if s.reflector_trasero else "apagado"
                st.caption(
                    f"**Sobre el reflector trasero.** Llega al fondo el {_pct(llega_fondo)} de "
                    f"los fotones que entran. Con el reflector {estado_ref}, este color produce "
                    f"corriente con el {_pct(eqe_aqui)} de sus fotones; con el reflector "
                    f"{'apagado' if s.reflector_trasero else 'encendido'} lo haría con el "
                    f"{_pct(eqe_otro)}.")
        else:
            st.markdown("#### El espectro solar")
            m1, m2 = st.columns(2)
            m1.metric("Corriente fotogenerada", f"{1e3 * j_celda:.2f} mA/cm²".replace(".", ","),
                      help="Ya descontada la sombra de la malla. Es la misma que usa la Pestaña 3.")
            m2.metric("Techo del espectro", f"{1e3 * reparto.j_maxima:.1f} mA/cm²".replace(".", ","),
                      help="Si cada fotón entre 300 y 1200 nm diera un par colectado.")
            j_otro = reparto_otro.j_sc * (1.0 - grid_otro.fraccion_sombra)
            st.info(
                f"De cada 100 fotones del Sol, {100 * k * sum(fr[c] for c in CLAVES_COLECTADAS):.0f} "
                f"terminan como corriente. La mayor pérdida es la reflexión "
                f"({_pct(k * fr['reflejados'])}), seguida de los pares que mueren en la "
                f"superficie frontal ({_pct(k * fr['emisor_superficie'])}).")
            st.caption(
                f"**Sobre el reflector trasero.** Con el reflector "
                f"{'encendido' if s.reflector_trasero else 'apagado'} la corriente es "
                f"{optics_plots._coma(1e3 * j_celda)} mA/cm²; con el reflector "
                f"{'apagado' if s.reflector_trasero else 'encendido'} sería "
                f"{optics_plots._coma(1e3 * j_otro)} mA/cm². La diferencia sale entera del "
                f"rojo lejano y el infrarrojo, el único rango que llega al fondo de la celda.")

    # ------------------------------------------------------------ rayos
    st.divider()
    st.markdown("### ¿Hasta dónde llega cada color?")
    st.plotly_chart(optics_plots.rayos_de_penetracion(campo, union,
                                                      lam if modo == "color" else None),
                    use_container_width=True)
    st.caption(
        "Cada rayo representa la luz de un color que entra por la cara superior. El coeficiente "
        "de absorción del silicio aumenta muchísimo al acortarse la longitud de onda, porque un "
        "fotón con más energía tiene más formas de excitar un electrón; por eso el violeta se "
        "apaga en unas decenas de nanómetros y el infrarrojo cercano a la banda prohibida puede "
        "recorrer milímetros. El eje de profundidad es logarítmico: cada marca es diez veces más "
        "honda que la anterior. La curva punteada es la profundidad 1/α de todos los colores, "
        "medida sobre el espesor real de la celda."
    )

    # ------------------------------------------------------------ mapa λ-x
    st.divider()
    st.markdown("### ¿A qué profundidad se absorbe cada color?")
    st.plotly_chart(optics_plots.mapa_absorcion(campo, union, lam if modo == "color" else None),
                    use_container_width=True)
    st.caption(
        "Es el mapa de generación en el plano longitud de onda-profundidad. Cada fila es un "
        "color y cada columna una capa de silicio; el brillo indica qué fracción de los fotones de "
        "ese color que entraron se absorbe en esa capa. Las capas son cada vez más gruesas hacia el "
        "fondo, doce por cada factor diez de profundidad, y con esa división la franja brillante "
        "de cada color queda centrada en su profundidad característica. Avanzando hacia la "
        "derecha, es decir hacia adentro de la celda, la franja sube hacia colores cada vez más "
        "largos: el violeta y el azul se agotan cerca de la superficie, mientras el rojo y el "
        "infrarrojo siguen absorbiéndose en lo hondo de la base. Las dos líneas responden a qué "
        "profundidad se ha absorbido la mitad y el 90 % de cada color; por encima del punto donde "
        "una línea se corta, esos colores salen de la celda antes de alcanzar esa fracción."
    )

    # ------------------------------------------------------------ generación
    st.divider()
    st.markdown("### ¿Dónde nacen los pares y cuáles producen corriente?")
    if modo == "espectro":
        g = campo.generacion_total()
        titulo_g = "Pares creados por el espectro solar completo"
        unidad = "pares / cm³·s"
    else:
        g = campo.G[:, i_lam]
        titulo_g = f"Pares creados por la luz de {lam:.0f} nm"
        unidad = "pares / cm³·s·nm"
    y_max = float(np.max(g)) / max(s.irradiancia_soles, 1e-6) * config.RANGOS["irradiancia_soles"][1] * 1.05
    st.plotly_chart(optics_plots.generacion_por_destino(campo.x_cm, g, destinos, union, W_um,
                                                        titulo_g, unidad, y_max),
                    use_container_width=True)
    st.caption(
        "La altura total de la curva es la tasa de generación G(x): cuántos pares se crean por "
        "segundo en cada centímetro cúbico a esa profundidad. Cae con la profundidad porque la luz "
        "se va agotando. La banda verde son los pares que llegarán a la juntura; su suma sobre toda "
        "la profundidad, multiplicada por la carga del electrón, es exactamente la corriente "
        "fotogenerada. El eje vertical está fijo en el máximo de 1,5 soles, así que al bajar la "
        "irradiancia la curva se encoge de verdad. Como el eje de profundidad es logarítmico, el "
        "área aparente de cada banda no es proporcional a la cantidad de pares; los porcentajes de "
        "la leyenda sí lo son."
    )
    with st.expander("Del fotón absorbido a la corriente eléctrica, paso a paso", expanded=True):
        st.markdown(
            "1. **Absorción.** El fotón entrega toda su energía a un electrón de la banda de "
            "valencia, que salta a la banda de conducción. Nace un par: un electrón libre y un "
            "hueco, que es la ausencia de un electrón y se mueve como una carga positiva.\n"
            "2. **Difusión.** En las regiones neutras de la celda —el emisor y la base— no hay "
            "campo eléctrico que empuje al par. El portador minoritario (el hueco en el emisor n, "
            "el electrón en la base p) se mueve al azar, y su supervivencia decide el destino del "
            "par, porque los mayoritarios sobran.\n"
            "3. **Recombinación.** Si durante ese recorrido el minoritario encuentra una superficie "
            "o un defecto, se recombina con un mayoritario y la energía se pierde como calor o "
            "como un fotón infrarrojo. Cuánto alcanza a recorrer lo mide la longitud de difusión.\n"
            "4. **Separación.** Si alcanza el borde de la zona de depleción, el campo eléctrico "
            "interno lo arrastra al otro lado en picosegundos: el electrón queda en el emisor y el "
            "hueco en la base. Separados por la juntura, ya no pueden recombinarse.\n"
            "5. **Corriente.** Esa separación acumula electrones en el emisor y huecos en la base. "
            "Con un circuito conectado, cada electrón sale por los dedos de plata, recorre la carga "
            "entregando su energía y vuelve por el contacto de aluminio. Cada par que completa el "
            "camino aporta una carga elemental a la corriente.\n\n"
            "Por eso lo pintado de verde en el gráfico es la parte de la luz absorbida que se "
            "convierte en electricidad: pares que ya nacieron y que además sobrevivirán hasta la "
            "juntura. Los que no alcanzan a llegar calientan la celda."
        )

    # ------------------------------------------------------------ destino según profundidad
    st.divider()
    st.markdown("### Si un par nace a cierta profundidad, ¿qué probabilidad tiene de llegar a la juntura?")
    if modo == "color":
        marca = float(cm_a_um(1.0 / campo.alpha[i_lam]))
        marca_txt = f"la luz de {lam:.0f} nm se absorbe en torno a {_prof(marca)}"
    else:
        g_tot = campo.generacion_total()
        acum = np.concatenate([[0.0], np.cumsum(np.diff(campo.x_cm) * (g_tot[:-1] + g_tot[1:]) / 2)])
        marca = float(cm_a_um(np.interp(0.5 * acum[-1], acum, campo.x_cm)))
        marca_txt = f"la mitad de los pares del espectro nace antes de {_prof(marca)}"
    if marca > W_um:
        marca = None
    st.plotly_chart(optics_plots.destino_segun_profundidad(campo.x_cm, destinos, union, W_um, tr,
                                                           marca, marca_txt),
                    use_container_width=True)
    st.caption(
        "Este gráfico no depende del color de la luz: describe la celda. Para cada profundidad "
        "responde qué le ocurriría a un par que naciera ahí. En la zona de depleción la respuesta "
        "es siempre la misma, el 100 % llega, porque el campo lo separa de inmediato. Hacia la "
        "cara frontal la probabilidad cae, porque el par tiene cerca una superficie que lo "
        "captura; hacia el fondo cae por la misma razón con la cara trasera, y además porque el "
        "camino a la juntura es largo y el volumen tiene tiempo de recombinarlo. El borde de la "
        "banda verde es la probabilidad de colección f_c(x) del enunciado. Combinado con el "
        "gráfico anterior explica todo: la luz que se absorbe donde este gráfico es verde produce "
        "corriente, y la que se absorbe donde es rojo, calor."
    )

    # ------------------------------------------------------------ balance
    st.divider()
    st.markdown("### El balance completo")
    st.plotly_chart(optics_plots.sankey_de_fotones(
        fr, fs, j_maxima_ma=1e3 * reparto.j_maxima if modo == "espectro" else None,
        modo=modo, lambda_nm=lam), use_container_width=True)
    st.caption(
        "Cada banda sigue a un grupo de fotones y su grosor es proporcional a cuántos son. De "
        "izquierda a derecha: primero las pérdidas ópticas, que ocurren antes de crear un par; "
        "después el lugar donde se absorbe la luz que entró; al final, el destino de los pares. "
        "Los destinos de la derecha suman exactamente el 100 %, y que lo hagan es una de las "
        "verificaciones que el monitor revisa en vivo. Pasando el cursor sobre una banda se ve su "
        "valor" + (" y la corriente a la que equivale." if modo == "espectro" else ".")
    )

    # ------------------------------------------------------------ viaje del fotón
    st.divider()
    st.markdown("### El viaje de un fotón")
    st.write(
        "Un solo fotón, seguido de principio a fin. Cada bifurcación del camino se sortea con las "
        "probabilidades del modelo para esta celda y este color"
        + (" —el color mismo se sortea del espectro solar—" if modo == "espectro" else "")
        + ". Puede terminar en corriente o perderse en cualquiera de las etapas; lanzando varios se "
        "ve con qué frecuencia ocurre cada cosa. También se puede forzar un destino para estudiar "
        "un camino en particular."
    )
    v1, v2 = st.columns([3, 1])
    with v1:
        forzar = st.selectbox(
            "Destino del fotón",
            options=["azar", "juntura", "superficie", "volumen", "refleja"],
            format_func={"azar": "Al azar, con las probabilidades del modelo",
                         "juntura": "Forzar: el par llega a la juntura y produce corriente",
                         "superficie": "Forzar: el par muere en una superficie",
                         "volumen": "Forzar: el par se recombina en el volumen",
                         "refleja": "Forzar: el fotón se refleja en la superficie"}.get)
    with v2:
        s.setdefault("viaje_semilla", 1)
        st.write("")
        if st.button("Lanzar otro fotón", use_container_width=True):
            s.viaje_semilla += 1
    dict_viaje, ficha = _figura_viaje(
        campo, union, tr, destinos, huella, fs, float(celsius_a_kelvin(s.T_c)), 1e3 * j_celda,
        modo, lam, s.viaje_semilla, forzar, mecanismos)
    st.plotly_chart(FiguraAnimada.desde_diccionario(dict_viaje), use_container_width=True)
    st.caption(
        f"Fotón de **{ficha['lambda_nm']:.0f} nm** · {optics_plots._coma(ficha['energia_eV'])} eV · se refleja con "
        f"probabilidad {_pct(ficha['R'])} · el 63 % de su color se absorbe antes de "
        f"{_prof(ficha['1/alpha_um'])}. En reposo la figura muestra el final del viaje; el botón lo "
        f"reproduce y la barra permite saltar a cada etapa. La escala vertical es esquemática "
        f"—cada región recibe un alto suficiente para verse, con su profundidad real rotulada a la "
        f"izquierda— y la forma del camino de difusión es ilustrativa: el modelo entrega la "
        f"probabilidad de cada destino, no la trayectoria de un portador."
    )

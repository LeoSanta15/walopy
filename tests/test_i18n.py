"""Infraestructura de idiomas: orden de prioridad, validación, respaldo al español, hilos/asyncio y traducción de lo que se muestra.

El catálogo inglés real llega en la fase 2; aquí se prueba el mecanismo con un catálogo inglés de prueba (``catalogo_en``).
"""
from __future__ import annotations

import asyncio
import threading

import pytest

import walopy as wl
from walopy import _i18n

CLAVE_ERROR = "utils.error.as_positive.debe_ser_numero_finito_positivo"
CLAVE_P0 = "queuing.clave_params.mm1.p0_prob_sistema_vacio"
CLAVE_COL = "queuing.cabecera.to_frame.tasa_llegada"


@pytest.fixture
def catalogo_en(monkeypatch):
    """Catálogo inglés de prueba con unas pocas claves (el resto recurre al español)."""
    en = {
        CLAVE_ERROR: "'{name}' must be a finite positive number, got {value!r}.",
        CLAVE_P0: "P0 (empty-system probability)",
        CLAVE_COL: "λ (arrival rate)",
        "queuing.etiqueta.summary.tasa_llegada": "(arrival rate)",
        "columnas.columna_df.global.sobrecargada": "Overloaded",
        "columnas.columna_df.global.estacion": "Station",
        "columnas.columna_df.global.tiempo_ciclo": "Cycle_time",
        "columnas.columna_df.global.tiempo_ocioso": "Idle_time",
    }
    monkeypatch.setitem(_i18n.CATALOGOS, "en", en)
    return en


# --- idioma activo -----------------------------------------------------------------------------------------------------------------
def test_el_idioma_por_defecto_es_espanol():
    assert wl.get_language() == "es"


def test_set_language_y_get_language():
    wl.set_language("en")
    assert wl.get_language() == "en"
    wl.set_language("es")
    assert wl.get_language() == "es"


def test_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("WALOPY_LANG", "en")
    assert wl.get_language() == "en"
    monkeypatch.setenv("WALOPY_LANG", "EN_us")      # se normaliza: minúsculas y dos letras
    assert wl.get_language() == "en"


@pytest.mark.parametrize("valor", ["", "fr", "xx", "  "])
def test_valor_desconocido_de_entorno_vuelve_a_espanol(monkeypatch, valor):
    monkeypatch.setenv("WALOPY_LANG", valor)
    assert wl.get_language() == "es"


def test_prioridad_contexto_sobre_global_sobre_entorno(monkeypatch):
    monkeypatch.setenv("WALOPY_LANG", "en")
    wl.set_language("es")                  # el global gana al entorno
    assert wl.get_language() == "es"
    with wl.language("en"):                # el contexto gana al global
        assert wl.get_language() == "en"
        with wl.language("es"):            # anidado
            assert wl.get_language() == "es"
        assert wl.get_language() == "en"
    assert wl.get_language() == "es"


def test_el_contexto_restablece_el_idioma_aunque_haya_una_excepcion():
    with pytest.raises(RuntimeError), wl.language("en"):
        raise RuntimeError("fallo dentro del bloque")
    assert wl.get_language() == "es"


@pytest.mark.parametrize("malo", ["fr", "", "EN", None, 3, ["en"], True])
def test_idioma_no_admitido_lanza_valueerror(malo):
    with pytest.raises(ValueError, match="Idioma no admitido"):
        wl.set_language(malo)
    with pytest.raises(ValueError, match="Idioma no admitido"):
        wl.language(malo)                  # valida al crear el contexto, no al entrar


def test_idioma_no_admitido_no_cambia_el_estado():
    with pytest.raises(ValueError):
        wl.set_language("fr")
    assert wl.get_language() == "es"


def test_el_contexto_no_se_filtra_a_otros_hilos():
    visto = []
    with wl.language("en"):
        h = threading.Thread(target=lambda: visto.append(wl.get_language()))
        h.start()
        h.join()
        assert wl.get_language() == "en"
    assert visto == ["es"]                  # un hilo nuevo no hereda el contexto del que lo lanzó


def test_el_contexto_esta_aislado_entre_tareas_asyncio():
    async def tarea(lang, pausa):
        with wl.language(lang):
            await asyncio.sleep(pausa)
            return wl.get_language()

    async def principal():
        return await asyncio.gather(tarea("en", 0.02), tarea("es", 0.01), tarea("en", 0.0))

    assert asyncio.run(principal()) == ["en", "es", "en"]
    assert wl.get_language() == "es"


# --- t(): respaldo y formato -----------------------------------------------------------------------------------------------------
def test_t_en_espanol_formatea_la_plantilla():
    assert _i18n.t(CLAVE_ERROR, name="x", value=-1) == "'x' debe ser un número finito y positivo, se recibió -1."


def test_t_en_ingles_usa_el_catalogo_ingles(catalogo_en):
    with wl.language("en"):
        assert _i18n.t(CLAVE_ERROR, name="x", value=-1) == "'x' must be a finite positive number, got -1."


def test_t_recurre_al_espanol_si_falta_la_clave_en_ingles(catalogo_en):
    clave = "queuing.cabecera.to_frame.servidores"      # no está en el catálogo inglés de prueba
    with wl.language("en"):
        assert _i18n.t(clave) == _i18n.ES[clave] == "c (servidores)"


def test_t_devuelve_la_clave_si_no_existe_en_ningun_idioma():
    assert _i18n.t("no.existe.esta.clave") == "no.existe.esta.clave"
    with wl.language("en"):
        assert _i18n.t("no.existe.esta.clave") == "no.existe.esta.clave"


def test_un_marcador_se_puede_llamar_clave():
    """``t(clave, /, **datos)``: la clave es solo posicional, así un marcador llamado ``clave`` no choca."""
    assert _i18n.t("inventory.error.clave.falta_clave", nombre="items", i=3, clave="demand") == "items[3]: falta la clave 'demand'."


# --- lo que se ve cambia con el idioma; lo que es API no ---------------------------------------------------------------------------
def test_los_errores_se_traducen(catalogo_en):
    with wl.language("en"), pytest.raises(ValueError, match="must be a finite positive number"):
        wl.mm1(-1.0, 3.0)
    with pytest.raises(ValueError, match="debe ser un número finito y positivo"):
        wl.mm1(-1.0, 3.0)


def test_las_claves_de_params_son_fijas_y_summary_traduce_la_etiqueta(catalogo_en):
    r = wl.mm1(2.0, 3.0)
    assert "P0 (prob. de sistema vacío)" in r.params
    with wl.language("en"):
        assert "P0 (prob. de sistema vacío)" in r.params            # decisión D1: la clave no cambia
        assert "P0 (empty-system probability)" in r.summary()
    assert "P0 (prob. de sistema vacío)" in r.summary()


def test_las_cabeceras_de_to_frame_se_traducen_al_crear(catalogo_en):
    assert "λ (tasa de llegada)" in wl.mm1(2.0, 3.0).to_frame().columns
    with wl.language("en"):
        assert "λ (arrival rate)" in wl.mm1(2.0, 3.0).to_frame().columns


def test_columna_encuentra_la_columna_aunque_cambie_el_idioma(catalogo_en):
    df = wl.mm1(2.0, 3.0).to_frame()                                  # creada en español
    with wl.language("en"):
        assert _i18n.columna(df, CLAVE_COL) == "λ (tasa de llegada)"  # decisión D2: se busca en cualquier idioma
    with wl.language("en"):
        df_en = wl.mm1(2.0, 3.0).to_frame()
    assert _i18n.columna(df_en, CLAVE_COL) == "λ (arrival rate)"      # y desde el español, la columna inglesa
    assert _i18n.columna(df, "no.existe.esta.clave") == "no.existe.esta.clave"


def test_etiqueta_param_traduce_las_conocidas_y_deja_las_demas(catalogo_en):
    with wl.language("en"):
        assert _i18n.etiqueta_param("P0 (prob. de sistema vacío)") == "P0 (empty-system probability)"
        assert _i18n.etiqueta_param("clave de la persona usuaria") == "clave de la persona usuaria"


def test_un_idioma_que_cambia_entre_crear_y_graficar_no_rompe_plotting(catalogo_en):
    pytest.importorskip("plotly")
    from walopy.plotting import plot_line_balance

    r = wl.line_balance(["A", "B"], [5.0, 9.0], 10.0)                # estaciones creadas en español
    with wl.language("en"):
        fig = plot_line_balance(r)
    assert len(fig.data) >= 1

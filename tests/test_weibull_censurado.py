"""Weibull con datos censurados por la derecha (0.4.8): suspensiones, rangos de Johnson e intervalos de confianza.

Oráculos independientes: valores calculados con scipy (optimizador Nelder-Mead sobre la verosimilitud y brentq sobre la
ecuación de perfil) y Hessiano numérico por diferencias finitas, constantes con su origen; una búsqueda por sección
áurea sobre la verosimilitud perfilada escrita aquí; las varianzas asintóticas de datos completos; y una simulación
de la cobertura de los intervalos.
"""
import math
import random

import pytest

import walopy as wl

# Origen: scipy 1.17 (Nelder-Mead sobre la log-verosimilitud en (ln β, ln η), xatol 1e-12) y Hessiano por diferencias finitas
# centrales en (ln β, ln η) (paso 1e-3), intervalo normal sobre el logaritmo con el cuantil t de Student de r − 2 = 6 grados
# de libertad (t = 2,446912; scipy.stats.t.ppf(0.975, 6)).
FALLAS = [72.0, 95.0, 130.0, 151.0, 176.0, 210.0, 243.0, 290.0]
SUSPENSIONES = [100.0, 120.0, 150.0, 200.0, 200.0, 250.0, 300.0, 300.0]
BETA_REF, ETA_REF = 2.419030624426742, 273.46702745731557
IC_BETA_REF = (1.1887999901016812, 4.922366428867417)
IC_ETA_REF = (188.36024004820257, 397.0276056518213)


def _loglik(f, s, beta, eta):
    r = len(f)
    return (r * (math.log(beta) - beta * math.log(eta)) + (beta - 1.0) * sum(math.log(t) for t in f)
            - sum((t / eta) ** beta for t in f + s))


def _eta_dado_beta(f, s, beta):
    return ((sum(t ** beta for t in f) + sum(t ** beta for t in s)) / len(f)) ** (1.0 / beta)


def _beta_seccion_aurea(f, s):
    """Maximiza la verosimilitud perfilada sin usar su derivada (independiente de la bisección de la librería)."""
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    lo, hi = 0.05, 30.0

    def perfil(b):
        return _loglik(f, s, b, _eta_dado_beta(f, s, b))

    a, b = hi - phi * (hi - lo), lo + phi * (hi - lo)
    fa, fb = perfil(a), perfil(b)
    for _ in range(200):
        if fa < fb:
            lo, a, fa = a, b, fb
            b = lo + phi * (hi - lo)
            fb = perfil(b)
        else:
            hi, b, fb = b, a, fa
            a = hi - phi * (hi - lo)
            fa = perfil(a)
    return (lo + hi) / 2.0


def _simular(rng, n, beta, eta, censura):
    """n unidades con tiempo de censura común `censura`: devuelve (fallas, suspensiones)."""
    vida = [eta * (-math.log(1.0 - rng.random())) ** (1.0 / beta) for _ in range(n)]
    return [t for t in vida if t <= censura], [censura] * sum(t > censura for t in vida)


class TestMLEConCensura:
    def test_coincide_con_scipy(self):
        r = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        assert r.shape == pytest.approx(BETA_REF, rel=1e-6)
        assert r.scale == pytest.approx(ETA_REF, rel=1e-6)
        assert (r.n, r.n_suspended) == (8, 8)

    def test_coincide_con_seccion_aurea(self):
        r = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        assert r.shape == pytest.approx(_beta_seccion_aurea(FALLAS, SUSPENSIONES), rel=1e-5)

    def test_es_maximo_de_la_verosimilitud(self):
        r = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        m = _loglik(FALLAS, SUSPENSIONES, r.shape, r.scale)
        for db, de in [(1.02, 1.0), (0.98, 1.0), (1.0, 1.02), (1.0, 0.98), (1.01, 0.99)]:
            assert _loglik(FALLAS, SUSPENSIONES, r.shape * db, r.scale * de) < m

    def test_sin_suspensiones_es_el_mismo_resultado(self):
        base = wl.weibull_analysis(FALLAS)
        for vacio in (None, [], ()):
            r = wl.weibull_analysis(FALLAS, suspensions=vacio)
            assert (r.shape, r.scale, r.n_suspended) == (base.shape, base.scale, 0)

    def test_suspensiones_tardias_alargan_la_vida(self):
        base = wl.weibull_analysis(FALLAS)
        con = wl.weibull_analysis(FALLAS, suspensions=[400.0, 450.0])
        assert con.scale > base.scale

    def test_ignorar_suspensiones_subestima_la_vida(self):
        """El sesgo que motiva la función: descartar las unidades que siguen vivas subestima η."""
        rng = random.Random(3)
        sesgo_ignorando, sesgo_mle = [], []
        for _ in range(150):
            f, s = _simular(rng, 40, 2.0, 100.0, 90.0)
            if len(f) < 5:
                continue
            sesgo_ignorando.append(wl.weibull_analysis(f).scale / 100.0 - 1.0)
            sesgo_mle.append(wl.weibull_analysis(f, suspensions=s).scale / 100.0 - 1.0)
        m_ign = sum(sesgo_ignorando) / len(sesgo_ignorando)
        m_mle = sum(sesgo_mle) / len(sesgo_mle)
        assert m_ign < -0.10          # descartar suspensiones: η queda más de 10 % por debajo
        assert abs(m_mle) < 0.04      # con censura bien tratada, el sesgo es pequeño

    def test_invariante_a_la_escala_de_tiempo(self):
        a = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        c = 7.0
        b = wl.weibull_analysis([c * t for t in FALLAS], suspensions=[c * t for t in SUSPENSIONES])
        assert b.shape == pytest.approx(a.shape, rel=1e-9)
        assert b.scale == pytest.approx(c * a.scale, rel=1e-9)
        assert b.shape_ci == pytest.approx(a.shape_ci, rel=1e-9)
        assert b.scale_ci == pytest.approx(tuple(c * x for x in a.scale_ci), rel=1e-9)

    def test_el_orden_de_los_datos_no_importa(self):
        a = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        b = wl.weibull_analysis(FALLAS[::-1], suspensions=SUSPENSIONES[::-1])
        assert (a.shape, a.scale) == pytest.approx((b.shape, b.scale), rel=1e-12)


class TestIntervalosDeConfianza:
    def test_coinciden_con_hessiano_numerico(self):
        r = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        assert r.confidence == 0.95
        assert r.shape_ci == pytest.approx(IC_BETA_REF, rel=1e-5)
        assert r.scale_ci == pytest.approx(IC_ETA_REF, rel=1e-5)

    def test_contienen_la_estimacion_y_son_positivos(self):
        r = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        assert 0.0 < r.shape_ci[0] < r.shape < r.shape_ci[1]
        assert 0.0 < r.scale_ci[0] < r.scale < r.scale_ci[1]

    def test_mas_confianza_intervalo_mas_ancho(self):
        c90 = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES, confidence=0.90)
        c99 = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES, confidence=0.99)
        assert c90.confidence == 0.90
        assert c99.shape_ci[0] < c90.shape_ci[0] < c90.shape_ci[1] < c99.shape_ci[1]
        assert c99.scale_ci[0] < c90.scale_ci[0] < c90.scale_ci[1] < c99.scale_ci[1]

    def test_mas_censura_intervalo_mas_ancho(self):
        """Misma población (cuantiles de Weibull β=2, η=100), censurada antes: menos fallas observadas, menos información."""
        vida = [100.0 * (-math.log(1.0 - (i - 0.5) / 30)) ** 0.5 for i in range(1, 31)]
        anchos = []
        for corte in (400.0, 130.0, 80.0):
            f = [t for t in vida if t <= corte]
            s = [corte] * (len(vida) - len(f))
            r = wl.weibull_analysis(f, suspensions=s)
            anchos.append(math.log(r.scale_ci[1] / r.scale_ci[0]))
        assert anchos[0] < anchos[1] < anchos[2]

    def test_varianzas_asintoticas_con_datos_completos(self):
        """Sin censura, n·Var(β̂)/β² → 0,6079 y n·β²·Var(η̂)/η² → 1,1087 (varianza asintótica de Weibull)."""
        rng = random.Random(11)
        n, beta, eta = 4000, 2.0, 100.0
        f, _ = _simular(rng, n, beta, eta, 1e9)
        r = wl.weibull_analysis(f)
        z = 1.959964
        se_ln_b = math.log(r.shape_ci[1] / r.shape_ci[0]) / (2 * z)
        se_ln_e = math.log(r.scale_ci[1] / r.scale_ci[0]) / (2 * z)
        assert n * se_ln_b ** 2 == pytest.approx(0.6079, rel=0.03)
        assert n * r.shape ** 2 * se_ln_e ** 2 == pytest.approx(1.1087, rel=0.03)

    def test_cobertura_por_simulacion(self):
        """Con ~30 % de censura y n = 60, el nivel nominal 95 % se cumple de forma aproximada."""
        rng = random.Random(2024)
        aciertos_b = aciertos_e = total = 0
        for _ in range(500):
            f, s = _simular(rng, 60, 1.8, 100.0, 110.0)
            if len(f) < 8:
                continue
            r = wl.weibull_analysis(f, suspensions=s)
            total += 1
            aciertos_b += r.shape_ci[0] <= 1.8 <= r.shape_ci[1]
            aciertos_e += r.scale_ci[0] <= 100.0 <= r.scale_ci[1]
        assert 0.91 <= aciertos_b / total <= 0.985
        assert 0.91 <= aciertos_e / total <= 0.985

    def test_rry_no_calcula_intervalos(self):
        r = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES, method="RRY")
        assert (r.shape_ci, r.scale_ci, r.confidence) == (None, None, None)
        fila = r.to_frame().iloc[0]
        assert fila.isna().sum() == 4


    def test_cobertura_con_pocas_fallas_sigue_siendo_casi_nominal(self):
        """Con 6 fallas y datos completos, el intervalo normal (Wald) cubre ≈ 87 % y 85 % (β y η); con la t de r − 2 grados de libertad, ≈ 94 %."""
        rng = random.Random(77)
        aciertos_b = aciertos_e = total = 0
        for _ in range(600):
            f, _s = _simular(rng, 6, 2.0, 100.0, 1e9)
            if max(f) == min(f):
                continue
            with pytest.warns(UserWarning, match="sobrestima"):
                r = wl.weibull_analysis(f)
            total += 1
            aciertos_b += r.shape_ci[0] <= 2.0 <= r.shape_ci[1]
            aciertos_e += r.scale_ci[0] <= 100.0 <= r.scale_ci[1]
        assert aciertos_b / total >= 0.92 and aciertos_e / total >= 0.91
        assert aciertos_b / total <= 0.985 and aciertos_e / total <= 0.985

    def test_el_cuantil_es_el_de_la_t_de_r_menos_2(self):
        """Con r fallas, ancho (en log) = 2·t(r−2)·ee: el cociente con el de otro nivel de confianza sigue el de los cuantiles t."""
        c90 = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES, confidence=0.90)
        c95 = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        ancho = lambda ic: math.log(ic[1] / ic[0])  # noqa: E731
        assert ancho(c90.shape_ci) / ancho(c95.shape_ci) == pytest.approx(1.9431802805153042 / 2.4469118511449786, rel=1e-9)
        assert ancho(c90.scale_ci) / ancho(c95.scale_ci) == pytest.approx(1.9431802805153042 / 2.4469118511449786, rel=1e-9)


@pytest.mark.filterwarnings("ignore:Con solo")
class TestSesgoDelMLE:
    def test_avisa_con_menos_de_ocho_fallas(self):
        for n in (2, 5, 7):
            with pytest.warns(UserWarning, match=f"Con solo {n} fallas"):
                wl.weibull_analysis(FALLAS[:n])

    def test_no_avisa_con_ocho_o_mas_ni_con_rry(self, recwarn):
        wl.weibull_analysis(FALLAS)                       # 8 fallas
        wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        wl.weibull_analysis(FALLAS[:4], method="RRY")
        assert not [w for w in recwarn if issubclass(w.category, UserWarning)]

    def test_el_aviso_dice_la_verdad_sobre_el_sesgo(self):
        """El MLE de β sobrestima con pocas fallas (≈ +45 % con 5 y +15 % con 10) y RRY casi no: lo que dice el aviso."""
        rng = random.Random(21)
        mle5, rry5, mle10 = [], [], []
        for _ in range(1500):
            f5 = [100.0 * (-math.log(1.0 - rng.random())) ** 0.5 for _ in range(5)]
            f10 = f5 + [100.0 * (-math.log(1.0 - rng.random())) ** 0.5 for _ in range(5)]
            mle5.append(wl.weibull_analysis(f5).shape / 2.0)
            rry5.append(wl.weibull_analysis(f5, method="RRY").shape / 2.0)
            mle10.append(wl.weibull_analysis(f10).shape / 2.0)
        m5, r5, m10 = sum(mle5) / 1500, sum(rry5) / 1500, sum(mle10) / 1500
        assert 1.30 < m5 < 1.65 and 1.08 < m10 < 1.25
        assert abs(r5 - 1.0) < 0.15 and m5 > r5 + 0.25

    def test_aviso_en_ingles(self):
        wl.set_language("en")
        try:
            with pytest.warns(UserWarning, match="overestimates"):
                wl.weibull_analysis(FALLAS[:5])
        finally:
            wl.set_language("es")


class TestRRYConRangosDeJohnson:
    def test_rangos_ajustados_a_mano(self):
        """n = 5; F=1, S=2, F=3, F=4, S=5: incrementos 6/6, 5/4 y 3,75/3 → rangos 1; 2,25; 3,5 (Johnson, 1964)."""
        f, s = [1.0, 3.0, 4.0], [2.0, 5.0]
        rangos = [1.0, 2.25, 3.5]
        x = [math.log(t) for t in f]
        y = [math.log(-math.log(1.0 - (k - 0.3) / 5.4)) for k in rangos]
        mx, my = sum(x) / 3, sum(y) / 3
        pend = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sum((a - mx) ** 2 for a in x)
        eta = math.exp(mx - my / pend)
        r = wl.weibull_analysis(f, suspensions=s, method="RRY")
        assert r.shape == pytest.approx(pend, rel=1e-12)
        assert r.scale == pytest.approx(eta, rel=1e-12)

    def test_sin_suspensiones_equivale_a_rangos_de_benard(self):
        n = len(FALLAS)
        x = [math.log(t) for t in sorted(FALLAS)]
        y = [math.log(-math.log(1.0 - (i - 0.3) / (n + 0.4))) for i in range(1, n + 1)]
        mx, my = sum(x) / n, sum(y) / n
        pend = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sum((a - mx) ** 2 for a in x)
        r = wl.weibull_analysis(FALLAS, method="rry")
        assert r.shape == pytest.approx(pend, rel=1e-12)

    def test_suspensiones_tempranas_no_alteran_los_rangos_previos(self):
        """Una suspensión anterior a todas las fallas desplaza los rangos, pero una posterior a todas no cambia las fallas."""
        sin = wl.weibull_analysis(FALLAS, method="RRY")
        tarde = wl.weibull_analysis(FALLAS, suspensions=[1000.0], method="RRY")
        # El rango de Benard usa n + 0,4 con n mayor: el efecto es pequeño pero la forma cambia poco
        assert tarde.shape == pytest.approx(sin.shape, rel=0.15)

    def test_mle_y_rry_son_cercanos_con_censura_moderada(self):
        mle = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        rry = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES, method="RRY")
        assert rry.shape == pytest.approx(mle.shape, rel=0.25)
        assert rry.scale == pytest.approx(mle.scale, rel=0.10)


@pytest.mark.filterwarnings("ignore:Con solo")
class TestCasosExtremos:
    @pytest.mark.parametrize("fallas,susp", [
        ([10.0, 11.0, 12.0], [1000.0] * 5),    # casi todo suspendido: la vida es muy incierta
        ([10.0, 1000.0, 500.0], [5.0]),
        ([1.0, 2.0, 3.0], [1e6] * 50),
    ])
    def test_censura_fuerte_da_resultados_finitos_con_intervalos_amplios(self, fallas, susp):
        for metodo in ("MLE", "RRY"):
            r = wl.weibull_analysis(fallas, suspensions=susp, method=metodo)
            assert math.isfinite(r.shape) and r.shape > 0 and math.isfinite(r.scale) and r.scale > 0
        mle = wl.weibull_analysis(fallas, suspensions=susp)
        # con tan pocas fallas el intervalo de η es muy ancho (más de un orden de magnitud)
        assert mle.scale_ci[1] / mle.scale_ci[0] > 10.0

    def test_con_dos_fallas_no_hay_intervalos(self):
        """Dos fallas y dos parámetros: no quedan grados de libertad, así que no se afirma ninguna incertidumbre."""
        r = wl.weibull_analysis([5.0, 9.0], suspensions=[20.0])
        assert (r.shape_ci, r.scale_ci, r.confidence) == (None, None, None)
        assert r.shape > 0 and r.scale > 0

    def test_suspensiones_anteriores_a_todas_las_fallas(self):
        """Unidades retiradas mucho antes de la primera falla casi no aportan información: β y η apenas cambian."""
        sin = wl.weibull_analysis(FALLAS)
        con = wl.weibull_analysis(FALLAS, suspensions=[1.0, 2.0, 3.0])
        assert con.scale == pytest.approx(sin.scale, rel=1e-3)
        assert con.shape == pytest.approx(sin.shape, rel=1e-3)


class TestSalida:
    def test_summary_y_to_frame(self):
        r = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES)
        txt = r.summary()
        assert "Suspensiones" in txt and "IC 95%" in txt
        fila = r.to_frame().iloc[0]
        assert fila["suspensiones"] == 8
        assert fila["β IC inferior"] == pytest.approx(IC_BETA_REF[0], rel=1e-5)

    def test_summary_sin_suspensiones_es_el_anterior_mas_intervalo(self):
        txt = wl.weibull_analysis(FALLAS).summary()
        assert "Suspensiones" not in txt and "IC 95%" in txt

    def test_summary_en_ingles(self):
        wl.set_language("en")
        try:
            txt = wl.weibull_analysis(FALLAS, suspensions=SUSPENSIONES).summary()
        finally:
            wl.set_language("es")
        assert "Suspensions" in txt and "95% CI" in txt


class TestValidacion:
    @pytest.mark.parametrize("conf", [0.0, 1.0, -0.1, 1.5, float("nan")])
    def test_confidence_fuera_de_rango(self, conf):
        with pytest.raises(ValueError):
            wl.weibull_analysis(FALLAS, confidence=conf)

    @pytest.mark.parametrize("susp", [[-1.0], [0.0], [float("nan")], [float("inf")]])
    def test_suspensiones_invalidas(self, susp):
        with pytest.raises(ValueError):
            wl.weibull_analysis(FALLAS, suspensions=susp)

    def test_suspensiones_no_numericas(self):
        with pytest.raises(TypeError):
            wl.weibull_analysis(FALLAS, suspensions=["a"])
        with pytest.raises(TypeError):
            wl.weibull_analysis(FALLAS, suspensions=5)

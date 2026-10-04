"""Inventario de todo el texto visible para la persona usuaria en ``src/walopy`` (base de la internacionalización).

Recorre el código con ``ast`` y extrae, por clase de texto, cada cadena con sus marcadores de formato:

========== =====================================================================================
tipo        qué es
========== =====================================================================================
error       mensaje de una excepción (``raise ValueError(...)``)
aviso       mensaje de ``warnings.warn``
etiqueta    texto de ``summary()`` y ``__str__``
cabecera    nombre de columna que se muestra en ``to_frame()`` (constantes ``_COL_*``, ``rename``, ``DataFrame``)
clave_params clave legible de ``result.params`` (RIESGO: una clave que cambia con el idioma rompe ``params[...]``)
kpi         ``name``/``unit``/``formula`` de ``KPINode``
grafica     títulos, ejes, leyendas, anotaciones (matplotlib y plotly)
cli         ayuda y mensajes de ``python -m walopy``
modelo      nombre de modelo o método que se muestra (``model=``, ``method=``): notación de dominio con partes traducibles
valor_por_defecto  nombre o valor de argumento por defecto (``Artículo{i}``, ``item_name="Artículo"``): cambiaría con el idioma
columna_df  clave de diccionario o columna de un ``DataFrame`` que devuelve una función pública: forma parte de la API
acceso_columna  lectura de una columna o clave por su texto (``df["Estación"]``): acoplamiento que rompe al traducir
texto_en_expresion  texto escondido dentro de la expresión de un f-string (``x or "ninguna"``)
nombre_arg  nombre de argumento dentro de un mensaje (``capacity[{i}]``): NO se traduce
sin_clasificar  cadena que parece texto visible y no encaja en ninguna clase anterior (revisión manual)
========== =====================================================================================

Uso::

    python scripts/inventario_i18n.py            # falla si queda algún texto visible literal en src/ fuera del catálogo
    python scripts/inventario_i18n.py --src DIR --escribir ref.json --informe ref.md   # inventario de otro directorio (p. ej. un tag)

El JSON **no guarda números de línea** (cambiarían con cualquier edición); identifica cada texto por módulo, función y plantilla.
La referencia anterior a la migración (v0.3.0) está en ``docs/auditoria/inventario_i18n_base.json`` y es la fuente del catálogo en español.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src" / "walopy"

KW_GRAFICA = {
    "label", "title", "xlabel", "ylabel", "text", "name", "xaxis_title", "yaxis_title", "legend_title_text",
    "hovertext", "hovertemplate", "legend_title", "zlabel", "annotation_text",
}
METODOS_GRAFICA = {"set_title", "set_xlabel", "set_ylabel", "suptitle", "annotate", "text", "set_label", "bar_label", "add_annotation"}
FUNCIONES_ETIQUETA = {"summary", "__str__"}
PARRAFOS_FUNCION = ("frame",)  # to_frame, curve_to_frame, ...
STOP = {"de", "la", "el", "los", "las", "un", "una", "que", "se", "en", "y", "o", "a", "por", "con", "del", "al", "para", "es", "no"}
ESTILO = {"steps-mid", "--", "-", ":", "-.", "o", "s", "^", "x", "+", "*", "k", "w", "left", "right", "center", "top", "bottom", "bar", "pie",
          "top left", "top right", "bottom left", "bottom right", "x unified", "y unified", "closest", "Blues", "Greens", "Reds"}
KW_MODELO = {"model", "method", "policy", "rule", "strategy"}
CLAVES_DE_DATOS = {"Q_eoq", "Q_optimal"}   # claves internas de diccionarios (no son texto para la persona usuaria)
IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")
NOMBRE_ARG = re.compile(r"^[a-z_][a-z0-9_]*(\[[^\]]*\])+$")      # solo el nombre; si sigue texto («... debe ser > 0.») es un mensaje
ESPECIFICACION = re.compile(r"^[<>^=]?[+\- ]?#?0?\d*,?(\.\d+)?[bcdeEfFgGnosxX%]?$")   # «.4g», «<16», «.2%»: formato numérico, no texto
CLAVE_CATALOGO = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+){2,3}(_\d+)?$")      # «inventory.error.eoq.demanda_positiva»
POR_DEFECTO = re.compile(r"^[^\s{}]+\{[^{}]+\}$")
SIMBOLICO = re.compile(r"^[A-Z0-9/ ()+\-.,:=%^_|<>≤≥²μλρσ]+$")  # notación de dominio: «M/M/1», «G/G/1», «OEE»


def _esc(texto: str) -> str:
    return texto.replace("{", "{{").replace("}", "}}")


def _slug(plantilla: str) -> str:
    sin_marcadores = re.sub(r"\{[^{}]*\}", " ", plantilla.replace("{{", "").replace("}}", ""))
    ascii_ = unicodedata.normalize("NFKD", sin_marcadores).encode("ascii", "ignore").decode()
    palabras = [p for p in re.findall(r"[a-z0-9]+", ascii_.lower()) if p not in STOP and len(p) > 1]
    return "_".join(palabras[:5]) or "texto"


class Marcadores:
    """Asigna nombres únicos a las expresiones de un f-string."""

    def __init__(self) -> None:
        self.items: list[dict] = []
        self._nombres: Counter = Counter()

    def agregar(self, valor: ast.AST, conversion: int, formato: str) -> str:
        if isinstance(valor, ast.Name):
            base, simple = valor.id, True
        elif isinstance(valor, ast.Attribute):
            base, simple = valor.attr, True
        else:
            base, simple = "expr", False
        self._nombres[base] += 1
        nombre = base if self._nombres[base] == 1 else f"{base}{self._nombres[base]}"
        self.items.append({
            "nombre": nombre,
            "expresion": ast.unparse(valor),
            "conversion": {-1: "", 114: "r", 115: "s", 97: "a"}[conversion],
            "formato": formato,
            "simple": simple,
            "_nodo": valor,          # solo para la migración; no se serializa
        })
        suf = ("!" + self.items[-1]["conversion"] if self.items[-1]["conversion"] else "") + (":" + formato if formato else "")
        return "{" + nombre + suf + "}"


def plantilla(nodo: ast.AST, marc: Marcadores) -> str | None:
    """Convierte una cadena, f-string, concatenación o ``.format()`` en una plantilla; ``None`` si no es una cadena."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return _esc(nodo.value)
    if isinstance(nodo, ast.JoinedStr):
        partes: list[str] = []
        for v in nodo.values:
            if isinstance(v, ast.Constant):
                partes.append(_esc(str(v.value)))
            elif isinstance(v, ast.FormattedValue):
                spec = ""
                if v.format_spec is not None:
                    spec = "".join(str(x.value) for x in v.format_spec.values if isinstance(x, ast.Constant))
                partes.append(marc.agregar(v.value, v.conversion, spec))
        return "".join(partes)
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        a, b = plantilla(nodo.left, marc), plantilla(nodo.right, marc)
        return None if a is None or b is None else a + b
    return None


def _cadenas_de(expr: ast.AST) -> list[ast.AST]:
    """Cadenas candidatas dentro de una expresión (``title or f"…"``, ``a if c else b``)."""
    if isinstance(expr, ast.BoolOp):
        return [x for v in expr.values for x in _cadenas_de(v)]
    if isinstance(expr, ast.IfExp):
        return _cadenas_de(expr.body) + _cadenas_de(expr.orelse)
    if isinstance(expr, (ast.Constant, ast.JoinedStr, ast.BinOp)):
        return [expr]
    return []


def _candidato_visible(texto: str) -> bool:
    """True si la cadena parece texto para una persona (no un identificador, color, estilo ni símbolo)."""
    t = texto.strip()
    sin = re.sub(r"\{[^{}]*\}", "", t.replace("{{", "").replace("}}", ""))
    return bool(sin) and t not in CLAVES_DE_DATOS and not (IDENT.match(t) or t in ESTILO or t.startswith("#") or len(sin) <= 2 or not _tiene_letras(t)
                              or SIMBOLICO.match(sin) or t.startswith("__"))


def _tiene_letras(texto: str) -> bool:
    return bool(re.search(r"[A-Za-zÁÉÍÓÚÜáéíóúüñÑ]", re.sub(r"\{[^{}]*\}", "", texto.replace("{{", "").replace("}}", ""))))


class Extractor(ast.NodeVisitor):
    def __init__(self, modulo: str) -> None:
        self.modulo = modulo
        self.pila: list[str] = []
        self.entradas: list[dict] = []
        self.capturados: set[int] = set()      # ids de nodos ya clasificados (y de sus hijos)
        self.docstrings: set[int] = set()
        self.indirectos: list[dict] = []

    # --- utilidades -----------------------------------------------------------------------------------
    @property
    def funcion(self) -> str:
        return ".".join(self.pila) if self.pila else "<módulo>"

    def _marcar(self, nodo: ast.AST) -> None:
        for n in ast.walk(nodo):
            self.capturados.add(id(n))

    def _registrar(self, tipo: str, nodo: ast.AST, extra: dict | None = None) -> None:
        if id(nodo) in self.capturados:
            return
        marc = Marcadores()
        texto = plantilla(nodo, marc)
        if texto is None or CLAVE_CATALOGO.match(texto):
            return
        self._marcar(nodo)                       # aunque no tenga letras: sus hijos (formatos, claves) no son textos sueltos
        self._ocultos(marc, tipo, nodo)
        if not _tiene_letras(texto):
            return
        if NOMBRE_ARG.match(texto):
            tipo = "nombre_arg"
        elif tipo in {"sin_clasificar", "cabecera"} and POR_DEFECTO.match(texto) and marc.items and "frame" not in self.funcion:
            tipo = "valor_por_defecto"
        self.entradas.append({"tipo": tipo, "modulo": self.modulo, "funcion": self.funcion, "es": texto,
                              "marcadores": marc.items, "nodo": nodo, **(extra or {})})

    def _ocultos(self, marc: Marcadores, tipo: str, padre_nodo: ast.AST) -> None:
        """Texto o clave de columna escondidos DENTRO de una expresión de un f-string: ``x or 'ninguna'``, ``row['Artículo']``."""
        for m in marc.items:
            padre = m["_nodo"]
            claves = {id(n.slice) for n in ast.walk(padre) if isinstance(n, ast.Subscript)}
            for n in ast.walk(padre):
                if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
                    continue
                if id(n) in claves:
                    if _candidato_visible(n.value) and (" " in n.value.strip() or re.search(r"[áéíóúñÁÉÍÓÚÑ()/]", n.value) or n.value[0].isupper()):
                        self.entradas.append({"tipo": "acceso_columna", "modulo": self.modulo, "funcion": self.funcion, "es": _esc(n.value),
                                              "marcadores": [], "nodo": n, "anidado": True, "padre_nodo": padre_nodo})
                elif _tiene_letras(n.value) and not ESPECIFICACION.match(n.value) and n.value not in CLAVES_DE_DATOS \
                        and not CLAVE_CATALOGO.match(n.value):
                    self.entradas.append({"tipo": "texto_en_expresion", "modulo": self.modulo, "funcion": self.funcion, "es": _esc(n.value),
                                          "marcadores": [], "nodo": n, "anidado": True, "padre": tipo, "padre_nodo": padre_nodo})

    # --- recorrido ------------------------------------------------------------------------------------
    def _docstring(self, nodo: ast.AST) -> None:
        cuerpo = getattr(nodo, "body", [])
        if cuerpo and isinstance(cuerpo[0], ast.Expr) and isinstance(cuerpo[0].value, ast.Constant) and isinstance(cuerpo[0].value.value, str):
            self.docstrings.add(id(cuerpo[0].value))

    def visit_Module(self, nodo: ast.Module) -> None:
        self._docstring(nodo)
        self.generic_visit(nodo)

    def visit_ClassDef(self, nodo: ast.ClassDef) -> None:
        self._docstring(nodo)
        self.pila.append(nodo.name)
        self.generic_visit(nodo)
        self.pila.pop()

    def visit_FunctionDef(self, nodo: ast.FunctionDef) -> None:
        self._docstring(nodo)
        self.pila.append(nodo.name)
        for defecto in [*nodo.args.defaults, *[d for d in nodo.args.kw_defaults if d is not None]]:
            if isinstance(defecto, ast.Constant) and isinstance(defecto.value, str) and _candidato_visible(defecto.value):
                self._registrar("valor_por_defecto", defecto)
        if any(p in nodo.name for p in PARRAFOS_FUNCION):
            for n in ast.walk(nodo):
                if isinstance(n, (ast.JoinedStr, ast.Constant)) and id(n) not in self.docstrings:
                    if isinstance(n, ast.JoinedStr) or (isinstance(n.value, str) and _candidato_visible(n.value)):
                        self._registrar("cabecera", n)
        if nodo.name in FUNCIONES_ETIQUETA:
            claves = {id(n.slice) for n in ast.walk(nodo) if isinstance(n, ast.Subscript)}      # t['x'], row['Q*']: claves de datos
            for n in ast.walk(nodo):
                if isinstance(n, (ast.JoinedStr, ast.Constant)) and id(n) not in self.docstrings and id(n) not in claves:
                    self._registrar("etiqueta", n)
        self.generic_visit(nodo)
        self.pila.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Assign(self, nodo: ast.Assign) -> None:
        for destino in nodo.targets:
            if isinstance(destino, ast.Name) and destino.id == "__all__":
                self._marcar(nodo)
            if isinstance(destino, ast.Name) and destino.id.endswith("label"):
                for c in _cadenas_de(nodo.value):
                    self._registrar("etiqueta", c)
            if isinstance(destino, ast.Name) and destino.id.startswith("_COL_") and isinstance(nodo.value, ast.Dict):
                for clave in nodo.value.keys:
                    if clave is not None:
                        self._marcar(clave)
                for valor in nodo.value.values:
                    self._registrar("cabecera", valor, {"constante": destino.id})
        self.generic_visit(nodo)

    def visit_Raise(self, nodo: ast.Raise) -> None:
        if isinstance(nodo.exc, ast.Call):
            for arg in nodo.exc.args:
                cand = _cadenas_de(arg)
                if cand:
                    for c in cand:
                        self._registrar("error", c)
                elif isinstance(arg, ast.Call) and getattr(arg.func, "id", "") in {"_t", "t"}:
                    continue                  # ya está en el catálogo
                elif isinstance(arg, (ast.Name, ast.Call, ast.Attribute, ast.Subscript)):
                    self.indirectos.append({"modulo": self.modulo, "funcion": self.funcion, "expresion": ast.unparse(arg)})
        self.generic_visit(nodo)

    def visit_Call(self, nodo: ast.Call) -> None:
        nombre = nodo.func.attr if isinstance(nodo.func, ast.Attribute) else getattr(nodo.func, "id", "")
        if nombre == "warn" and nodo.args:
            for c in _cadenas_de(nodo.args[0]):
                self._registrar("aviso", c)
        elif nombre == "KPINode":
            for kw in nodo.keywords:
                if kw.arg in {"name", "unit", "formula"}:
                    for c in _cadenas_de(kw.value):
                        self._registrar("kpi", c, {"campo": kw.arg})
        elif nombre == "rename":
            for kw in nodo.keywords:
                if kw.arg == "columns" and isinstance(kw.value, ast.Dict):
                    for v in kw.value.values:
                        self._registrar("cabecera", v)
        elif nombre == "DataFrame" and any(p in "".join(self.pila) for p in PARRAFOS_FUNCION):
            for a in nodo.args:
                if isinstance(a, ast.Dict):
                    for k in a.keys:
                        if k is not None:
                            self._registrar("cabecera", k)
            for kw in nodo.keywords:
                if kw.arg == "columns" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    for e in kw.value.elts:
                        self._registrar("cabecera", e)
        elif nombre in {"add_argument", "add_parser", "ArgumentParser"}:
            for kw in nodo.keywords:
                if kw.arg in {"help", "description", "epilog", "version"}:
                    for c in _cadenas_de(kw.value):
                        self._registrar("cli", c)
        elif nombre == "print" and self.modulo == "__main__":
            for a in nodo.args:
                for c in _cadenas_de(a):
                    self._registrar("cli", c)
        if nombre in METODOS_GRAFICA and nodo.args:
            for c in _cadenas_de(nodo.args[0]):
                self._registrar("grafica", c)
        for kw in nodo.keywords:
            if kw.arg == "param":
                for c in _cadenas_de(kw.value):
                    self._registrar("columna_df", c)
            if kw.arg in KW_MODELO:
                for c in _cadenas_de(kw.value):
                    if isinstance(c, ast.JoinedStr) or (isinstance(c, ast.Constant) and _candidato_visible(str(c.value))):
                        self._registrar("modelo", c, {"campo": kw.arg})
            if kw.arg in KW_GRAFICA and nombre not in {"KPINode", "DataFrame"}:
                for c in _cadenas_de(kw.value):
                    self._registrar("grafica", c, {"campo": kw.arg})
            if kw.arg == "params" and isinstance(kw.value, ast.Dict):
                for k in kw.value.keys:
                    if k is not None and isinstance(k, ast.Constant) and isinstance(k.value, str):
                        self._registrar("clave_params", k)
        self.generic_visit(nodo)

    def visit_Dict(self, nodo: ast.Dict) -> None:
        for k in nodo.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str) and id(k) not in self.capturados and _candidato_visible(k.value) \
                    and (" " in k.value.strip() or re.search(r"[áéíóúñÁÉÍÓÚÑ()/]", k.value) or k.value[0].isupper()):
                self._registrar("columna_df", k)
        self.generic_visit(nodo)

    def visit_Subscript(self, nodo: ast.Subscript) -> None:
        sl = nodo.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str) and id(sl) not in self.capturados and _candidato_visible(sl.value) \
                and (" " in sl.value.strip() or re.search(r"[áéíóúñÁÉÍÓÚÑ()/]", sl.value) or sl.value[0].isupper()):
            self._registrar("acceso_columna", sl)
        self.generic_visit(nodo)

    def visit_Constant(self, nodo: ast.Constant) -> None:
        self._sin_clasificar(nodo)

    def visit_JoinedStr(self, nodo: ast.JoinedStr) -> None:
        self._sin_clasificar(nodo)

    def _sin_clasificar(self, nodo: ast.AST) -> None:
        if id(nodo) in self.capturados or id(nodo) in self.docstrings:
            return
        if isinstance(nodo, ast.Constant):
            if not isinstance(nodo.value, str):
                return
            v = nodo.value
            if not _candidato_visible(v) or v == "walopy":
                return
            if " " not in v.strip() and not re.search(r"[áéíóúñÁÉÍÓÚÑ]", v) and not v[0].isupper():
                return
        self._registrar("grafica" if self.modulo == "plotting" else "sin_clasificar", nodo)


def _complejidad(entrada: dict) -> str:
    marc = entrada["marcadores"]
    if not marc:
        return "fija"
    if any(not m["simple"] for m in marc):
        return "compleja"
    if any(m["formato"] or m["conversion"] for m in marc):
        return "formato"
    return "simple"


def extraer(con_sitios: bool = False):
    crudas: list[dict] = []
    indirectos: list[dict] = []
    for archivo in sorted(SRC.glob("*.py")):
        if archivo.stem in {"_i18n", "_catalogo_es", "_catalogo_en"}:      # el catálogo contiene los textos a propósito
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        ex = Extractor(archivo.stem)
        ex.visit(arbol)
        crudas += ex.entradas
        indirectos += ex.indirectos
    # agrupar por (módulo, tipo, plantilla): un texto repetido es una sola clave con varios usos.
    # Las columnas de DataFrame devueltas por funciones públicas se agrupan por texto entre módulos: quien las crea y quien las lee usan la MISMA clave.
    grupos: dict[tuple, dict] = {}
    for e in crudas:
        modulo_grupo = "columnas" if e["tipo"] in {"columna_df", "acceso_columna"} else e["modulo"]
        k = (modulo_grupo, e["tipo"], e["es"])
        g = grupos.setdefault(k, {**{x: y for x, y in e.items() if x != "nodo"}, "usos": 0, "funciones": []})
        g["usos"] += 1
        calificada = f"{e['modulo']}.{e['funcion']}" if e["tipo"] in {"columna_df", "acceso_columna"} else e["funcion"]
        if calificada not in g["funciones"]:
            g["funciones"].append(calificada)
    entradas = sorted(grupos.values(), key=lambda g: (g["modulo"], g["tipo"], g["funciones"][0], g["es"]))
    vistas: Counter = Counter()
    for g in entradas:
        g["funcion"] = g["funciones"][0]
        compartida = g["tipo"] in {"columna_df", "acceso_columna"}
        funcion = "global" if compartida else (g["funcion"].split(".")[-1].strip("_<>").replace("módulo", "modulo") or "modulo")
        modulo = "columnas" if compartida else g["modulo"].strip("_")
        tipo = "columna_df" if g["tipo"] == "acceso_columna" else g["tipo"]
        base = f"{modulo}.{tipo}.{funcion}.{_slug(g['es'])}"
        if g["tipo"] == "acceso_columna":
            g["usa_clave"] = ""            # se resuelve abajo contra la columna creada con el mismo texto
            base = base.replace(".columna_df.", ".acceso_columna.")
            vistas[base] += 1
            g["clave"] = base if vistas[base] == 1 else f"{base}_{vistas[base]}"
            continue
        vistas[base] += 1
        g["clave"] = base if vistas[base] == 1 else f"{base}_{vistas[base]}"
    por_texto = {g["es"]: g["clave"] for g in entradas if g["tipo"] == "columna_df"}
    for g in entradas:
        g["complejidad"] = _complejidad(g)
        g["funciones"] = sorted(g["funciones"])
        if g["tipo"] == "acceso_columna":
            g["usa_clave"] = por_texto.get(g["es"], "")
    indirectos = sorted(indirectos, key=lambda i: (i["modulo"], i["funcion"], i["expresion"]))
    if con_sitios:
        clave_de = {(("columnas" if e["tipo"] in {"columna_df", "acceso_columna"} else e["modulo"]), e["tipo"], e["es"]): g
                    for g in entradas for e in [g]}
        return entradas, indirectos, crudas, clave_de
    return entradas, indirectos


def _serializable(e: dict) -> dict:
    """Campos del inventario (sin nodos AST ni números de línea)."""
    salida = {k: e[k] for k in ("clave", "tipo", "modulo", "funcion", "funciones", "usos", "complejidad", "es")}
    salida["marcadores"] = [{a: b for a, b in m.items() if a != "_nodo"} for m in e["marcadores"]]
    for extra in ("constante", "campo", "usa_clave", "padre"):
        if extra in e:
            salida[extra] = e[extra]
    return salida


def construir() -> dict:
    entradas, indirectos = extraer()
    return {
        "version": 1,
        "idioma_base": "es",
        "total": len(entradas),
        "usos": sum(e["usos"] for e in entradas),
        "entradas": [_serializable(e) for e in entradas],
        "indirectos": indirectos,
    }


def informe(datos: dict) -> str:
    e = datos["entradas"]
    tipos = sorted({x["tipo"] for x in e})
    mods = sorted({x["modulo"] for x in e})
    por_tm = defaultdict(int)
    por_tc = defaultdict(int)
    for x in e:
        por_tm[(x["modulo"], x["tipo"])] += 1
        por_tc[(x["tipo"], x["complejidad"])] += 1
    lineas = [
        "# INVENTARIO I18N — texto visible de walopy (generado)",
        "",
        "> Generado por `python scripts/inventario_i18n.py`; **no editar a mano**. Línea base **congelada** de los textos de v0.3.0 (antes de pasar al catálogo): `docs/auditoria/inventario_i18n_base.json`.",
        f"> {datos['total']} textos únicos, {datos['usos']} usos en el código. Idioma base: `{datos['idioma_base']}`.",
        "> Un texto repetido en un módulo cuenta una vez (clave única) y aparece con su número de usos.",
        "",
        "## Por tipo y módulo (textos únicos)",
        "",
        "| módulo | " + " | ".join(tipos) + " | total |",
        "|---|" + "---|" * (len(tipos) + 1),
    ]
    for m in mods:
        fila = [str(por_tm.get((m, t), 0) or "") for t in tipos]
        lineas.append(f"| `{m}` | " + " | ".join(fila) + f" | {sum(por_tm.get((m, t), 0) for t in tipos)} |")
    lineas.append("| **total** | " + " | ".join(str(sum(por_tm.get((m, t), 0) for m in mods)) for t in tipos) + f" | **{datos['total']}** |")
    lineas += ["", "## Complejidad de la plantilla", "",
               "`fija` sin variables · `simple` solo nombres · `formato` con `!r` o formato numérico (`:.6g`) · `compleja` con expresiones (llamadas, índices…).", "",
               "| tipo | fija | simple | formato | compleja |", "|---|---|---|---|---|"]
    for t in tipos:
        lineas.append(f"| {t} | " + " | ".join(str(por_tc.get((t, c), 0) or "") for c in ("fija", "simple", "formato", "compleja")) + " |")
    lineas += ["", "## Riesgos que detecta el inventario", ""]
    params = [x for x in e if x["tipo"] == "clave_params"]
    nombres = [x for x in e if x["tipo"] == "nombre_arg"]
    cols = [x for x in e if x["tipo"] == "columna_df"]
    acc = [x for x in e if x["tipo"] == "acceso_columna"]
    lineas.append(f"- **Columnas/claves de `DataFrame` devueltas directamente por funciones públicas: {len(cols)}**, y **{len(acc)} accesos por texto** (`df[\"Estación\"]`). Traducir una columna sin cambiar sus accesos rompe el código (p. ej. `plotting.py` lee `df[\"Tiempo_ciclo\"]`).")
    lineas.append(f"- **Nombres de argumento dentro de mensajes: {len(nombres)}** (`capacity[{{i}}]`…): no se traducen; el inventario los separa para no contarlos.")
    lineas.append(f"- **Claves de `params` legibles: {len(params)}.** Si cambian con el idioma, `result.params[«clave»]` deja de funcionar al cambiar de idioma (ver `PLAN_I18N.md`).")
    sin = [x for x in e if x["tipo"] == "sin_clasificar"]
    pd_ = [x for x in e if x["tipo"] == "valor_por_defecto"]
    lineas.append(f"- **Nombres generados por defecto: {len(pd_)}** (`Artículo{{i}}`, `escenario_{{n}}`): si dependen del idioma cambian los datos, no solo la presentación.")
    lineas.append(f"- **Textos sin clasificar: {len(sin)}** (revisión manual obligatoria antes de la fase 1).")
    comp = [x for x in e if x["complejidad"] == "compleja"]
    lineas.append(f"- **Plantillas con expresiones complejas: {len(comp)}** (hay que precalcular el valor antes de llamar a `t()`).")
    lineas.append(f"- **Mensajes construidos fuera de la excepción (`raise <variable>`): {len(datos['indirectos'])}** (no se pueden extraer sin leer el código).")
    lineas += ["", "## Textos sin clasificar", ""] + ([f"- `{x['modulo']}.{x['funcion']}`: {x['es']!r}" for x in sin] or ["_(ninguno)_"])
    lineas += ["", "## Mensajes indirectos", ""] + ([f"- `{x['modulo']}.{x['funcion']}`: `raise {x['expresion']}`" for x in datos["indirectos"]] or ["_(ninguno)_"])
    lineas += ["", "## Accesos a columnas por su texto (acoplamiento)", ""] + [f"- `{x['modulo']}.{x['funcion']}`: {x['es']!r}" for x in acc]
    lineas += ["", "## Columnas de DataFrame devueltas por funciones públicas", ""] + [f"- `{x['modulo']}.{x['funcion']}`: {x['es']!r}" for x in cols]
    lineas += ["", "## Nombres generados por defecto", ""] + [f"- `{x['modulo']}.{x['funcion']}`: {x['es']!r}" for x in pd_]
    lineas += ["", "## Claves de `params`", ""] + [f"- `{x['modulo']}.{x['funcion']}`: {x['es']!r}" for x in params]
    lineas += ["", "## Plantillas complejas", ""] + [f"- `{x['clave']}`: {x['es']!r} — " + ", ".join(f"`{m['nombre']}` = `{m['expresion']}`" for m in x["marcadores"] if not m["simple"]) for x in comp]
    return "\n".join(lineas) + "\n"


PERMITIDOS_TRAS_LA_MIGRACION = {"clave_params", "nombre_arg"}   # claves fijas de result.params (decisión D1) y nombres de argumentos


def main() -> int:
    global SRC
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", metavar="DIR", help="directorio del paquete a analizar (por defecto src/walopy)")
    ap.add_argument("--escribir", metavar="RUTA_JSON", help="escribe el inventario en JSON (y el informe en --informe)")
    ap.add_argument("--informe", metavar="RUTA_MD", help="escribe el informe en Markdown")
    args = ap.parse_args()
    if args.src:
        SRC = Path(args.src)
    datos = construir()
    if args.escribir:
        Path(args.escribir).write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if args.informe:
            Path(args.informe).write_text(informe(datos), encoding="utf-8")
        print(f"{datos['total']} textos únicos ({datos['usos']} usos) → {args.escribir}")
        return 0
    # modo por defecto: tras la migración no debe quedar ningún texto visible literal en el código
    restantes = [e for e in datos["entradas"] if e["tipo"] not in PERMITIDOS_TRAS_LA_MIGRACION]
    restantes += [{"tipo": "indirecto", "clave": f"{i['modulo']}.{i['funcion']}", "es": i["expresion"]} for i in datos["indirectos"]]
    for e in restantes:
        print(f"{e['tipo']:18s} {e.get('clave', '')}: {e['es']!r}")
    if restantes:
        print(f"\n{len(restantes)} texto(s) visible(s) fuera del catálogo: muévelos a _catalogo_es.py y usa _t(\"clave\").")
        return 1
    print("Sin textos visibles literales fuera del catálogo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

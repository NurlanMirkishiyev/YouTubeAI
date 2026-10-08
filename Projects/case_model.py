"""Faza 1.1 (istifadeci 2026-10-07) - strukturlu case modeli + deterministik qerar hesabi.

Plan sxeminde "model":
  {"variables": [{"name","value","unit","label"}], "before": {ad: ifade}, "after": {ad: ifade},
   "threshold": {"name","expr","rounding","meaning"}}
Ifadeler yalniz deyisen adlari, reqemler ve + - * / ( ) (× ÷ − de olar). Hesab ast ile (eval yox).
Neticeler (before/after/delta/threshold/insight) plan.model_result-a yazilir; ssenari onlardan "use exactly these
figures" kimi istifade edir, script_qa ise case_problems ile yoxlayir:
  a) qerar bolmesindeki her reqem modeldendir;
  b) case kemiyyeti ("100 customers") modelin deyerinden ferqlidirse xeta;
  c) naive: deyisen neytrallasdirilir (0 ve ya 1) - skript reqemi yalniz naive neticeye uygundursa
     "deyisen buraxilib" (real xeta sinfi: "40 customers x $5 = $200 extra", musteri itkisi unudulub).
"""
from __future__ import annotations

import ast
import math
import re

ROUNDING = {"ceil": math.ceil, "floor": math.floor, "round": round, "none": lambda v: v}
UNIT_MONEY, UNIT_PCT, UNIT_SHARE = "$", "%", "share"
_SYMBOLS = {"×": "*", "÷": "/", "−": "-", "–": "-", "x": None}
_OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}
FUNCS = {"ceil": math.ceil, "floor": math.floor, "round": round, "abs": abs, "min": min, "max": max}
SMALL_INT = 12          # kicik tam ededler (sira, "three mistakes") struktur sayilir
_YEAR = re.compile(r"(19|20)\d\d")


class CaseModelError(ValueError):
    """Plan modeli hesablanmir - plan yeniden istenmelidir. Mesaj ingiliscedir: LLM-e geri gedir (real probe)."""


def _parse(expr: str) -> ast.Expression:
    text = str(expr)
    for k, v in _SYMBOLS.items():
        if v:
            text = text.replace(k, v)
    try:
        tree = ast.parse(text.replace(",", ""), mode="eval")
    except SyntaxError as e:
        raise CaseModelError(f"formula cannot be parsed: {expr}") from e
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):       # real probe: LLM 'ceil(...)' yazir - yalniz FUNCS, keyword-suz
            if not (isinstance(node.func, ast.Name) and node.func.id in FUNCS and not node.keywords):
                raise CaseModelError(f"function not allowed (only ceil/floor/round/abs/min/max): {expr}")
            continue
        ok = isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.USub, ast.UAdd)) \
            or type(node) in _OPS or (isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
                                      and not isinstance(node.value, bool))
        if not ok:
            raise CaseModelError(f"not allowed in a formula ({type(node).__name__}): {expr}")
    return tree


def _names(tree: ast.AST) -> list[str]:
    return [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]


class _Scope:
    """Bir blokun (before/after/threshold) ifadeleri: ad -> deyer, dovri istinad tutulur."""

    def __init__(self, exprs: dict[str, str], env: dict[str, float], dims: dict[str, int],
                 ambiguous: set[str] | None = None, prior: "_Scope | None" = None):
        self.trees = {k: _parse(v) for k, v in exprs.items()}
        self.env, self.dims, self.ambiguous = env, dims, ambiguous or set()
        self.prior = prior       # after blokunda: before deyerleri (ozune istinad = evvelki deyer)
        self.reserved: set[str] = set()   # threshold adi - blok icinde isledile bilmez
        self.values: dict[str, float] = {}
        self.vdims: dict[str, int] = {}

    def get(self, name: str, stack: tuple[str, ...] = ()) -> float:
        if name in self.values:
            return self.values[name]
        if name in self.trees:
            if name in stack:
                raise CaseModelError("circular reference: " + " -> ".join((*stack, name)))
            value, dim = self._eval(self.trees[name].body, (*stack, name))
            self.values[name], self.vdims[name] = value, dim
            return value
        if name in self.ambiguous:
            raise CaseModelError(f"ambiguous name {name} (differs in before and after): write before_{name} or after_{name}")
        if name in self.env:
            return self.env[name]
        if self.prior and name in self.prior.trees:
            return self.prior.get(name)
        # real probe: bloklarin icinde de 'before_x' / 'after_x' yazilir
        before = self.prior or self
        if name.startswith("before_") and name[7:] in before.trees:
            return before.get(name[7:], stack if before is self else ())
        if name.startswith("after_") and self.prior and name[6:] in self.trees:
            return self.get(name[6:], stack)
        if self.reserved and name in self.reserved:
            raise CaseModelError(f"the threshold {name} is computed FROM before/after - never use it inside them")
        raise CaseModelError(f"unknown name: {name}")

    def dim(self, name: str) -> int:
        if name not in self.trees and self.prior and name in self.prior.trees:
            return self.prior.dim(name)
        before = self.prior or self
        if name not in self.trees and name not in self.dims:
            if name.startswith("before_") and name[7:] in before.trees:
                return before.dim(name[7:])
            if name.startswith("after_") and self.prior and name[6:] in self.trees:
                return self.dim(name[6:])
        if name in self.trees:
            self.get(name)
            return self.vdims[name]
        return self.dims.get(name, 0)

    def _eval(self, node: ast.AST, stack: tuple[str, ...]) -> tuple[float, int]:
        """-> (deyer, pul olcusu): $ * say = $, $ / $ = say."""
        if isinstance(node, ast.Constant):
            return float(node.value), 0
        if isinstance(node, ast.Name):
            if stack and node.id == stack[-1]:        # "hours = hours * 1.5": evvelki blok ve ya giris deyiseni
                if self.prior and node.id in self.prior.trees:
                    return self.prior.get(node.id), self.prior.dim(node.id)
                if node.id in self.env:
                    return self.env[node.id], self.dims.get(node.id, 0)
            v = self.get(node.id, stack)
            return v, self.dim(node.id)
        if isinstance(node, ast.Call):
            args = [self._eval(a, stack) for a in node.args]
            if not args:
                raise CaseModelError("function without arguments")
            try:
                return float(FUNCS[node.func.id](*[a for a, _ in args])), max(d for _, d in args)
            except (TypeError, ValueError) as e:
                raise CaseModelError(f"function error: {node.func.id}") from e
        if isinstance(node, ast.UnaryOp):
            v, d = self._eval(node.operand, stack)
            return (-v if isinstance(node.op, ast.USub) else v), d
        if isinstance(node, ast.BinOp):
            (a, da), (b, db) = self._eval(node.left, stack), self._eval(node.right, stack)
            try:
                value = _OPS[type(node.op)](a, b)
            except ZeroDivisionError as e:
                raise CaseModelError("division by zero") from e
            if isinstance(node.op, ast.Mult):
                return value, da + db
            if isinstance(node.op, ast.Div):
                return value, da - db
            return value, max(da, db)
        raise CaseModelError(f"not allowed in a formula: {type(node).__name__}")

    def all(self) -> dict[str, float]:
        return {k: self.get(k) for k in self.trees}


# ad hisseleri (snake_case sozleri) ile - "current" icindeki "rent" pul deyil
_MONEY_WORDS = {"price", "prices", "cost", "costs", "revenue", "fee", "fees", "wage", "wages", "salary", "spend",
                "spending", "profit", "payment", "rent", "income", "budget", "sale", "sales", "earnings", "amount",
                "dollars", "loan", "payroll", "expense", "expenses", "value", "savings"}
_PCT_WORDS = {"percent", "pct", "percentage"}
_SHARE_WORDS = {"rate", "share", "ratio", "retention", "churn", "conversion", "stay", "fraction"}


def infer_unit(name: str, value: float) -> str:
    """Vahidi verilmeyen deyisen (real probe: LLM 5 cehdde yazmadi) - addan deterministik."""
    words = [w for w in name.lower().split("_") if w.isalpha()]
    if _PCT_WORDS & set(words):
        return UNIT_PCT
    if _SHARE_WORDS & set(words) and 0 <= value <= 1:
        return UNIT_SHARE
    if _MONEY_WORDS & set(words):
        return UNIT_MONEY
    return next((w for w in reversed(words) if w.endswith("s")), words[-1] if words else "units")


def _variables(model: dict) -> list[dict]:
    out = []
    for v in model.get("variables") or []:
        name = str((v or {}).get("name") or "").strip()
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise CaseModelError(f"bad variable name: {name!r}")
        try:
            value = float(v.get("value"))
        except (TypeError, ValueError) as e:
            raise CaseModelError(f"variable value is not a number: {name}") from e
        unit = str(v.get("unit") or "").strip() or infer_unit(name, value)
        out.append({**v, "name": name, "value": value, "unit": unit})
    if not out:
        raise CaseModelError("model has no variables")
    return out


def _clean(v: float) -> float:
    r = round(v, 4)
    return float(int(r)) if float(r).is_integer() else r


def evaluate(model: dict) -> dict:
    """model -> model_result. Hesablanmayan ifade, namelum ad, dovri istinad, threshold yoxdursa CaseModelError."""
    if not isinstance(model, dict):
        raise CaseModelError("plan has no model")
    variables = _variables(model)
    th_name = str((model.get("threshold") or {}).get("name") or "") if isinstance(model.get("threshold"), dict) else ""
    if th_name and th_name in {v["name"] for v in variables}:
        th_name += "_threshold"            # real probe: threshold 'new_price' giris deyiseni ile eyni adda idi
    for v in variables:      # real probe: LLM 'before_profit', 'customers_needed' neticelerini giris kimi yazdi
        if v["name"].startswith(("before_", "after_", "delta_")):
            raise CaseModelError(f"variable is a computed result, not an input: {v['name']}")
    env = {v["name"]: v["value"] for v in variables}
    dims = {v["name"]: int(v["unit"] == UNIT_MONEY) for v in variables}
    blocks: dict[str, _Scope] = {}
    for key in ("before", "after"):
        exprs = model.get(key)
        if not isinstance(exprs, dict) or not exprs:
            raise CaseModelError(f"model has no '{key}'")
        for k, e in exprs.items():            # #96: real probe 'weekly_profit = weekly_sales' (xercsiz menfeet)
            if "profit" in str(k) and not re.search(r"[-−–]|profit", str(e)):
                raise CaseModelError(f"{key} {k} = {e} has no costs: profit is revenue minus costs - "
                                     f"subtract the costs (e.g. weekly_sales - weekly_costs)")
        blocks[key] = _Scope({str(k): str(e) for k, e in exprs.items()}, env, dims, prior=blocks.get("before"))
        blocks[key].reserved = {th_name} if th_name else set()
    before, after = blocks["before"].all(), blocks["after"].all()
    delta = {k: after[k] - before[k] for k in before if k in after}
    units = {k: (UNIT_MONEY if blocks["before"].dim(k) == 1 else "")
             for k in before} | {k: (UNIT_MONEY if blocks["after"].dim(k) == 1 else "") for k in after}

    th = model.get("threshold")
    if not isinstance(th, dict) or not str(th.get("expr") or "").strip():
        raise CaseModelError("threshold is required (decision topic)")
    th_env = dict(env)
    th_dims = dict(dims)
    for prefix, vals, scope in (("before_", before, blocks["before"]), ("after_", after, blocks["after"])):
        for k, v in vals.items():
            th_env[prefix + k], th_dims[prefix + k] = v, scope.dim(k)
    for k, v in delta.items():
        th_env["delta_" + k], th_dims["delta_" + k] = v, max(blocks["before"].dim(k), blocks["after"].dim(k))
    ambiguous = set()
    for k in set(before) | set(after):          # real probe: prefikssiz 'monthly_cost'
        vals = {round(x[k], 9) for x in (before, after) if k in x}
        if k in env:                            # eyni adli giris deyiseni ustundur
            continue
        if len(vals) > 1:
            ambiguous.add(k)
        elif k not in th_env:
            src = before if k in before else after
            th_env[k] = src[k]
            th_dims[k] = (blocks["before"] if k in before else blocks["after"]).dim(k)
    scope = _Scope({"__t": str(th["expr"])}, th_env, th_dims, ambiguous)
    raw = scope.get("__t")
    rounding = str(th.get("rounding") or "none").lower()
    if rounding not in ROUNDING:
        raise CaseModelError(f"unknown rounding: {rounding}")
    value = ROUNDING[rounding](raw)
    t_unit = str(th.get("unit") or (UNIT_MONEY if scope.dim("__t") == 1 else "")).strip()
    result = {
        "variables": {v["name"]: v["value"] for v in variables},
        "var_units": {v["name"]: v["unit"] for v in variables},
        "labels": {v["name"]: str(v.get("label") or v["name"]) for v in variables} | dict(model.get("labels") or {}),
        "before": {k: _clean(v) for k, v in before.items()},
        "after": {k: _clean(v) for k, v in after.items()},
        "delta": {k: _clean(v) for k, v in delta.items()},
        "units": units,
        "threshold": {"name": th_name or "threshold", "value": _clean(value), "raw": _clean(raw),
                      "rounding": rounding, "meaning": str(th.get("meaning") or ""), "unit": t_unit,
                      "expr": str(th["expr"])},
    }
    result["insight"] = insight(result)
    return result


def fmt(v: float, unit: str = "") -> str:
    if unit == UNIT_SHARE:
        return fmt(v * 100, UNIT_PCT)
    if v < 0:
        return "-" + fmt(-v, unit)
    s = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}".rstrip("0").rstrip(".")
    return f"${s}" if unit == UNIT_MONEY else f"{s}%" if unit == UNIT_PCT else s


def _label(result: dict, key: str) -> str:
    return str(result.get("labels", {}).get(key) or key.replace("_", " "))


def insight(result: dict) -> str:
    """En teeccublu netice, reqemli cumle: biri dusur, digeri qalxir (gelir -, menfeet +). Yoxdursa en boyuk nisbi
    deyisiklik."""
    d, b, a, u = result["delta"], result["before"], result["after"], result["units"]
    keys = [k for k in d if abs(d[k]) > 1e-9]
    falls = [k for k in keys if d[k] < 0]
    rises = [k for k in keys if d[k] > 0]
    if falls and rises:
        f, r = falls[0], rises[0]
        return (f"{_label(result, f).capitalize()} falls from {fmt(b[f], u[f])} to {fmt(a[f], u[f])}, yet "
                f"{_label(result, r)} rises from {fmt(b[r], u[r])} to {fmt(a[r], u[r])}.")
    if keys:
        k = max(keys, key=lambda x: abs(d[x]) / max(1e-9, abs(b[x])))
        verb = "rises" if d[k] > 0 else "falls"
        return f"{_label(result, k).capitalize()} {verb} from {fmt(b[k], u[k])} to {fmt(a[k], u[k])}."
    t = result["threshold"]
    meaning = t["meaning"].strip().rstrip(".")
    meaning = meaning[:1].lower() + meaning[1:]
    return f"Everything hinges on {fmt(t['value'], t['unit'])}: {meaning}."


def _derived(result: dict) -> list[float]:
    """Modelden birbasa cixan ara reqemler: qiymet ferqi ($55 - $50 = $5), qalan/geden musteri (40 x 0.85 = 34)."""
    vs, units = result["variables"], result["var_units"]
    out = []
    money = [vs[k] for k in vs if units.get(k) == UNIT_MONEY]
    out += [abs(x - y) for i, x in enumerate(money) for y in money[i + 1:]]
    shares = [vs[k] for k in vs if units.get(k) == UNIT_SHARE or (units.get(k) == UNIT_PCT)]
    shares = [s / 100 if s > 1 else s for s in shares]
    counts = [vs[k] for k in vs if units.get(k) not in (UNIT_MONEY, UNIT_PCT, UNIT_SHARE)]
    out += [abs(x - y) for i, x in enumerate(counts) for y in counts[i + 1:]]    # 150 musteri - 15 itki = 135
    for c in counts:
        for s in shares:
            out += [c * s, c * (1 - s)]
    for s in shares:
        out += [s * 100, (1 - s) * 100, s, 1 - s]
    return out


def allowed_numbers(result: dict) -> list[float]:
    """Skriptde isledile bilen case reqemleri: deyisenler, before/after/delta (modul), threshold, ara reqemler."""
    vals = list(result["variables"].values())
    for k, v in result["variables"].items():
        if result["var_units"].get(k) == UNIT_PCT:
            vals.append(v / 100)
    vals += list(result["before"].values()) + list(result["after"].values())
    vals += [abs(v) for v in (*result["before"].values(), *result["after"].values()) if v < 0]   # #94: "a loss of $450"
    vals += [abs(v) for v in result["delta"].values()]
    vals += [result["threshold"]["value"], result["threshold"]["raw"]]
    vals += _derived(result)
    out: list[float] = []
    for v in vals:
        v = _clean(float(v))
        if not any(abs(v - x) < 1e-6 for x in out):
            out.append(v)
    return out


def naive_values(model: dict) -> dict[float, str]:
    """Her deyisen ayrica neytrallasdirilir (0 ve 1) -> yeniden hesab. {naive netice: deyisen adi}.
    Duzgun neticelerle ust-uste dusenler cixarilir."""
    correct = evaluate(model)
    keep = allowed_numbers(correct)
    out: dict[float, str] = {}
    for v in _variables(model):
        for neutral in (0.0, 1.0):
            if abs(v["value"] - neutral) < 1e-12:
                continue
            vars2 = [{**x, "value": neutral} if x["name"] == v["name"] else x for x in model["variables"]]
            try:
                r = evaluate({**model, "variables": vars2})
            except CaseModelError:
                continue
            got = list(r["before"].values()) + list(r["after"].values()) + [abs(x) for x in r["delta"].values()]
            got.append(r["threshold"]["value"])
            for g in got:
                g = _clean(abs(g))
                if g <= SMALL_INT or any(abs(g - x) < 1e-6 for x in keep):
                    continue
                out.setdefault(g, v["name"])
    return out


def _in(v: float, pool: list[float]) -> bool:
    return any(abs(v - x) <= 1e-6 * max(1.0, abs(x)) for x in pool)


def _structural(v: float, span: str) -> bool:
    return (float(v).is_integer() and abs(v) <= SMALL_INT) or bool(_YEAR.fullmatch(span.strip("$")))


def _nouns(result: dict) -> dict[str, str]:
    """say deyiseninin ismi -> deyisen: unit 'customers' ve ya label-in son sozu."""
    out = {}
    for k, unit in result["var_units"].items():
        if unit in (UNIT_MONEY, UNIT_PCT, UNIT_SHARE):
            continue
        word = unit if re.fullmatch(r"[a-z]+", unit or "") else (re.findall(r"[a-z]+", _label(result, k).lower())
                                                                 or [""])[-1]
        if word:
            out[word.rstrip("s")] = k
    return out


def case_problems(markdown: str, plan: dict, source: dict | None = None) -> list[str]:
    """Deterministik, fail-closed: (a) qerar bolmesi, (b) case kemiyyeti, (c) naive (deyisen buraxilib)."""
    from math_check import find_numbers
    from script_qa import sections
    from visuals import figures
    result = plan.get("model_result")
    if not isinstance(result, dict):
        return ["plan.model_result yoxdur - case modeli hesablanmayib"]
    allowed = allowed_numbers(result)
    if source and source.get("figure") is not None:
        allowed.append(float(source["figure"]))
    naive = naive_values(plan.get("model") or {}) if plan.get("model") else {}
    secs = sections(markdown)
    body = [h for h in secs if h == "Hook" or h.startswith("Section ") or h == "Common Mistakes"]
    decision = [h for h in secs if h.startswith("Section ")][-1:]
    probs: list[str] = []
    for head in body:
        text = secs[head]
        shown = figures(text)
        for start, end, v in find_numbers(text):
            span = text[max(0, start - 1):end]
            if not _in(v, shown) or _structural(v, span):
                continue
            label = span if span.startswith("$") else text[start:end]
            if _in(v, allowed):
                continue
            if _in(v, list(naive)):
                name = next(n for x, n in naive.items() if abs(x - v) <= 1e-6 * max(1.0, abs(x)))
                probs.append(f"{head}: {label} - deyisen buraxilib ({name}); duzgun model neticesi istifade olunmali")
            elif head in decision:
                probs.append(f"{head}: {label} case modelinde yoxdur - qerar bolmesi yalniz model neticelerini deyir")
        for noun, var in _nouns(result).items():
            for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s+(?:\w+\s+)?" + noun + r"s?\b", text, re.I):
                v = float(m[1].replace(",", ""))
                if not _in(v, allowed) and not (_structural(v, m[1]) and v <= SMALL_INT):
                    probs.append(f"{head}: '{m[0]}' case modeli ile uygun deyil ({var} = "
                                 f"{fmt(result['variables'][var])})")
    probs += _decision_section_problems(secs[decision[0]], result, decision[0]) if decision else []
    return list(dict.fromkeys(probs))


def _decision_section_problems(text: str, result: dict, head: str) -> list[str]:
    """Faza 2.1: qerar bolmesi table + threshold vizuali ucun evvel/sonra cutunu (bir cumlede) ve esiyi deyir."""
    from math_check import find_numbers
    probs = []
    pair = False
    for sent in re.split(r"(?<=[.!?])\s+", text):
        vals = [abs(v) for _, _, v in find_numbers(sent)]          # #94: itki ishresiz deyilir ("loss of $450")
        if any(_in(abs(result["before"][k]), vals) and _in(abs(result["after"][k]), vals) for k in result["delta"]):
            pair = True
            break
    if not pair:
        probs.append(f"{head}: evvel/sonra cutu (eyni cumlede, mes. '{_pair_hint(result)}') deyilmir - table vizuali "
                     "ucun lazimdir")
    t = result["threshold"]
    vals = [v for _, _, v in find_numbers(text)]
    scale = (1, 100) if t["unit"] in (UNIT_PCT, UNIT_SHARE) or abs(t["raw"]) < 1 else (1,)   # #95: 40 != $4,000
    if not any(math.isclose(v, x * k, rel_tol=0.01, abs_tol=1e-6) for v in vals for x in (t["value"], t["raw"])
               for k in scale):
        probs.append(f"{head}: modelin threshold deyeri ({fmt(t['value'], t['unit'])}) deyilmir - qerar qaydasi "
                     "ve threshold vizuali ucun lazimdir")
    return probs


def _pair_hint(result: dict) -> str:
    k = next(iter(result["delta"]), None)
    if k is None:
        return ""
    u = result["units"].get(k, "")
    return f"{k.replace('_', ' ')} goes from {fmt(result['before'][k], u)} to {fmt(result['after'][k], u)}"


def figures_text(result: dict) -> str:
    """Ssenari telimati: 'use exactly these figures'."""
    u = result["units"]
    lines = [f"- {_label(result, k)}: {fmt(v, result['var_units'].get(k, ''))}" for k, v in result["variables"].items()]
    lines += [f"- {k.replace('_', ' ')}: before {fmt(result['before'][k], u.get(k, ''))}, after "
              f"{fmt(result['after'][k], u.get(k, ''))} (change {fmt(abs(result['delta'][k]), u.get(k, ''))})"
              for k in result["delta"]]
    t = result["threshold"]
    lines.append(f"- threshold ({t['meaning']}): {fmt(t['value'], t['unit'])}")
    return "\n".join(lines)


def names_hint(model: dict) -> str:
    """Redd mesaji ucun: formullarda isledile bilen adlar (real probe: LLM eyni namelum adi 5 defe tekrarladi)."""
    if not isinstance(model, dict):
        return ""
    vars_ = [str((v or {}).get("name")) for v in model.get("variables") or [] if isinstance(v, dict)]
    keys = list(dict.fromkeys([*(model.get("before") or {}), *(model.get("after") or {})]))
    return ("Formulas in before/after may use ONLY these variable names: " + ", ".join(vars_)
            + " (and other keys of the same block). threshold.expr may use those variables and: "
            + ", ".join(f"before_{k}, after_{k}, delta_{k}" for k in keys)
            + ". Every name in a formula must be in these lists; every variable needs a unit.")

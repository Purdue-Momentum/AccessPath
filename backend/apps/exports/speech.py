"""
Lane E. Turns MathML into plain English, the way a maths teacher would read it aloud.

Screen readers such as NVDA with MathCAT read MathML well on their own. Read-aloud tools
(Edge Read Aloud, Immersive Reader) and some screen readers only read the visible
characters, so an equation like W = integral s1 s2 F cos theta ds comes out as a jumble.
The words this module makes are shown under each equation, so every tool reads it properly.

Plain code, no AI: the same equation always gives the same words.
"""

import re

from lxml import etree

GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ϵ": "epsilon", "ζ": "zeta",
    "η": "eta", "θ": "theta", "ϑ": "theta", "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu", "ν": "nu",
    "ξ": "xi", "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon", "φ": "phi", "ϕ": "phi",
    "χ": "chi", "ψ": "psi", "ω": "omega",
    "Γ": "capital gamma", "Δ": "delta", "Θ": "capital theta", "Λ": "capital lambda", "Ξ": "capital xi",
    "Π": "capital pi", "Σ": "capital sigma", "Φ": "capital phi", "Ψ": "capital psi", "Ω": "capital omega",
}
FUNCTIONS = {"sin": "sine", "cos": "cosine", "tan": "tangent", "sec": "secant", "csc": "cosecant",
             "cot": "cotangent", "ln": "natural log", "log": "log", "exp": "exp", "max": "max", "min": "min",
             "lim": "the limit", "det": "determinant"}
OPERATORS = {
    "=": "equals", "+": "plus", "-": "minus", "−": "minus", "±": "plus or minus", "×": "times", "·": "dot",
    "⋅": "dot", "*": "times", "/": "over", "÷": "divided by", "<": "is less than", ">": "is greater than",
    "≤": "is less than or equal to", "≥": "is greater than or equal to", "≠": "is not equal to",
    "≈": "is approximately", "∝": "is proportional to", "→": "to", "⇒": "which gives", "⟹": "which gives",
    "∞": "infinity", "∂": "partial", "∇": "del", "∫": "the integral of", "∑": "the sum of",
    "∏": "the product of", "°": "degrees", "∘": "degrees", "′": "prime", "%": "percent", ",": ",",
    "(": "open bracket", ")": "close bracket", "[": "open bracket", "]": "close bracket",
    "{": "open bracket", "}": "close bracket", "|": "absolute value", "!": "factorial",
}
INVISIBLE = {"\u2061", "\u2062", "\u2063", "\u2064", ""}  # function application, invisible times and so on
FRACTION_NAMES = {("1", "2"): "one half", ("1", "3"): "one third", ("2", "3"): "two thirds",
                  ("1", "4"): "one quarter", ("3", "4"): "three quarters"}
ACCENTS = {"→": "vector {}", "⃗": "vector {}", "^": "{} hat", "ˆ": "{} hat", "¯": "{} bar", "‾": "{} bar",
           "˙": "{} dot", "¨": "{} double dot", "~": "{} tilde", "˜": "{} tilde"}
BIG_OPERATORS = {"∫": "integral", "∑": "sum", "∏": "product"}


def mathml_to_words(mathml: str) -> str:
    """'W = ∫ s1..s2 F cos θ ds' as MathML becomes 'W equals the integral from s sub 1 to s sub 2 of F ...'."""
    root = etree.fromstring(mathml.encode("utf-8"))
    words = _say(root)
    words = re.sub(r"\s+", " ", words)
    words = re.sub(r"\s+,", ",", words)
    words = re.sub(r",(\s*,)+", ",", words)
    return words.strip(" ,")


def _tag(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def _kids(el) -> list:
    return [c for c in el if isinstance(c.tag, str)]


def _text(el) -> str:
    return "".join(el.itertext()).strip()


def _unwrap(el):
    """An mrow holding a single element is just that element."""
    while _tag(el) == "mrow" and len(_kids(el)) == 1:
        el = _kids(el)[0]
    return el


def _is_upright_letter(el) -> bool:
    return _tag(el) == "mi" and el.get("mathvariant") == "normal" and len(_text(el)) == 1 and _text(el).isalpha()


def _is_simple(el) -> bool:
    """One letter, number or short name: needs no 'end fraction' to be understood."""
    el = _unwrap(el)
    tag = _tag(el)
    if tag in {"mi", "mn", "mtext"}:
        return True
    if tag in {"mrow", "mstyle"}:
        kids = _kids(el)
        if kids and all(_is_upright_letter(k) for k in kids):
            return True  # a word written in \mathrm, such as "out"
        return len(kids) <= 2 and all(_tag(k) in {"mi", "mn", "mtext"} for k in kids)
    if tag == "msub":
        return all(_is_simple(k) for k in _kids(el))
    return False


def _say(el) -> str:
    tag = _tag(el)
    kids = _kids(el)
    if tag in {"math", "mrow", "mstyle", "mpadded", "menclose", "merror"}:
        return " ".join(_say_row(kids))
    if tag == "semantics":
        return _say(kids[0]) if kids else ""
    if tag in {"mphantom", "mspace", "annotation", "annotation-xml", "none", "mprescripts"}:
        return ""
    if tag == "mi":
        text = _text(el)
        return FUNCTIONS.get(text) or GREEK.get(text) or OPERATORS.get(text) or text
    if tag == "mn":
        return _text(el)
    if tag == "mtext":
        return _text(el)
    if tag == "mo":
        text = _text(el)
        if text in INVISIBLE:
            return ""
        return OPERATORS.get(text, GREEK.get(text, text))
    if tag == "mfrac" and len(kids) == 2:
        top, bottom = _unwrap(kids[0]), _unwrap(kids[1])
        named = FRACTION_NAMES.get((_text(top), _text(bottom))) if _tag(top) == _tag(bottom) == "mn" else None
        if named:
            return named
        if _is_simple(top) and _is_simple(bottom):
            return f"{_say(top)} over {_say(bottom)}"
        return f"the fraction {_say(top)} over {_say(bottom)}, end fraction,"
    if tag == "msqrt":
        inner = " ".join(_say(k) for k in kids)
        return f"the square root of {inner}" + ("" if len(kids) == 1 and _is_simple(kids[0]) else ", end root,")
    if tag == "mroot" and len(kids) == 2:
        return f"the root of order {_say(kids[1])} of {_say(kids[0])}, end root,"
    if tag == "msup" and len(kids) == 2:
        return _power(_say(kids[0]), kids[1])
    if tag == "msub" and len(kids) == 2:
        if _text(kids[0]) == "lim":
            return f"the limit as {_say(kids[1])} of"
        return f"{_say(kids[0])} sub {_say(kids[1])}"
    if tag in {"msubsup", "munderover"} and len(kids) == 3:
        base, low, high = kids
        big = BIG_OPERATORS.get(_text(base))
        if big:
            return f"the {big} from {_say(low)} to {_say(high)} of"
        if tag == "msubsup":
            return _power(f"{_say(base)} sub {_say(low)}", high)
        return f"{_say(base)} from {_say(low)} to {_say(high)}"
    if tag == "munder" and len(kids) == 2:
        base, low = kids
        big = BIG_OPERATORS.get(_text(base))
        if big:
            return f"the {big} over {_say(low)} of"
        if _text(base) == "lim":
            return f"the limit as {_say(low)} of"
        return f"{_say(base)} under {_say(low)}"
    if tag == "mover" and len(kids) == 2:
        base, accent = kids
        pattern = ACCENTS.get(_text(accent))
        if pattern:
            return pattern.format(_say(base))
        return f"{_say(base)} over {_say(accent)}"
    if tag == "mtable":
        rows = [" , ".join(_say(cell) for cell in _kids(row)) for row in kids]
        return " ".join(f"row {i}: {row}," for i, row in enumerate(rows, start=1))
    return " ".join(_say(k) for k in kids) or _text(el)


def _say_row(kids: list) -> list[str]:
    """Reads a row, joining upright letters written in \\mathrm into one word ("out", not "o u t")."""
    words, letters = [], []
    for k in kids:
        if _is_upright_letter(k):
            letters.append(_text(k))
            continue
        if letters:
            words.append("".join(letters))
            letters = []
        words.append(_say(k))
    if letters:
        words.append("".join(letters))
    return words


def _power(base_words: str, exponent) -> str:
    text = _text(exponent)
    if text in {"∘", "°"}:
        return f"{base_words} degrees"
    if text in {"′", "'"}:
        return f"{base_words} prime"
    if text == "2":
        return f"{base_words} squared"
    if text == "3":
        return f"{base_words} cubed"
    if _is_simple(exponent):
        return f"{base_words} to the power {_say(exponent)}"
    return f"{base_words} to the power {_say(exponent)}, end power,"
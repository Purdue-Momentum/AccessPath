import pytest

from apps.exports.rendering import mathml
from apps.exports.speech import mathml_to_words


def words(latex):
    return mathml_to_words(mathml(latex, display="block"))


@pytest.mark.parametrize("latex, expected", [
    (r"U_{1 \to 2} = \int_{s_1}^{s_2} F \cos\theta \, ds",
     "U sub 1 to 2 equals the integral from s sub 1 to s sub 2 of F cosine theta d s"),
    (r"T = \frac{1}{2} m v^2", "T equals one half m v squared"),
    (r"T_1 + \sum U_{1 \to 2} = T_2", "T sub 1 plus the sum of U sub 1 to 2 equals T sub 2"),
    (r"P = \frac{dU}{dt} = \vec{F} \cdot \vec{v}", "P equals d U over d t equals vector F dot vector v"),
    (r"\eta = \frac{P_{\mathrm{out}}}{P_{\mathrm{in}}}", "eta equals P sub out over P sub in"),
    (r"U_g = -m g d \sin 30^\circ", "U sub g equals minus m g d sine 30 degrees"),
    (r"\sum_{i=1}^{n} F_i \Delta x_i", "the sum from i equals 1 to n of F sub i delta x sub i"),
    (r"\lim_{x \to 0} \frac{\sin x}{x} = 1", "the limit as x to 0 of sine x over x equals 1"),
    (r"E = m c^3", "E equals m c cubed"),
])
def test_equations_read_as_words(latex, expected):
    assert words(latex) == expected


def test_complex_parts_say_where_they_end():
    assert words(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}") == (
        "x equals the fraction minus b plus or minus the square root of b squared minus 4 a c, end root, "
        "over 2 a, end fraction")


def test_no_doubled_commas():
    assert ",," not in words(r"v = \sqrt{\frac{2 \times 30.6}{2}}").replace(" ", "")
"""ivtff / word_freq のテスト（python3 -m unittest discover voynich）。"""

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402
import word_freq  # noqa: E402

SAMPLE = """\
#=IVTFF Eva- 2.0 M 5
# comment line
<f1r>      <! $Q=A $P=A $F=a $B=1 $I=T $L=A $H=1 $C=1 $X=V>
<f1r.1,@P0>       <%>fachys.ykal.ar.ataiin.shol.shory.[cth:oto]res.y.kor.sholdy<!@254;>
<f1r.2,+P0>       sory.ckhar.or,y.kair.d?n.{ck}eo.r<->shy<~>oltchedy<$>
<f2r>      <! $Q=A $P=C $I=H $L=B $H=2>
<f2r.1,@Lf>       <@H=2>otol.f{c'hh}dar.@185;ol
"""


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.lines = list(ivtff.parse(SAMPLE.splitlines()))

    def test_lines_and_pages(self):
        self.assertEqual([ln.id for ln in self.lines], ["f1r.1", "f1r.2", "f2r.1"])
        self.assertEqual(self.lines[0].page.get("L"), "A")
        self.assertEqual(self.lines[2].page.get("H"), "2")
        self.assertEqual(self.lines[2].page.get("X"), "?")

    def test_locus(self):
        self.assertEqual(self.lines[0].position, "@")
        self.assertEqual(self.lines[0].locus_class, "P")
        self.assertEqual(self.lines[2].locus_type, "Lf")


class WordsTest(unittest.TestCase):
    def test_default(self):
        raw = "<%>shory.[cth:oto]res.or,y.d?n.{ck}eo.r<->shy<~>ol<!corr?><$>"
        self.assertEqual(ivtff.words(raw),
                         ["shory", "cthres", "or", "y", "ckeo", "r", "shy", "ol"])

    def test_options(self):
        raw = "[cth:oto]res.or,y.d?n"
        opts = ivtff.Options(alternative=1, comma_is_space=False, drop_uncertain=False)
        self.assertEqual(ivtff.words(raw, opts), ["otores", "ory", "d?n"])

    def test_rare(self):
        raw = "otol.@185;ol"
        self.assertEqual(ivtff.words(raw), ["otol", "@185;ol"])
        self.assertEqual(ivtff.words(raw, ivtff.Options(drop_rare=True)), ["otol"])


class StatsTest(unittest.TestCase):
    def test_zipf_ideal(self):
        counter = Counter({f"w{r}": round(10000 / r) for r in range(1, 200)})
        self.assertAlmostEqual(word_freq.zipf_exponent(counter), 1.0, places=1)

    def test_log_likelihood_sign(self):
        self.assertGreater(word_freq.log_likelihood(50, 10, 1000, 1000), 0)
        self.assertLess(word_freq.log_likelihood(10, 50, 1000, 1000), 0)
        self.assertAlmostEqual(word_freq.log_likelihood(10, 10, 1000, 1000), 0.0)


if __name__ == "__main__":
    unittest.main()

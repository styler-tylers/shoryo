"""ivtff / word_freq / affix のテスト（python3 -m unittest discover voynich）。"""

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import affix  # noqa: E402
import corpus  # noqa: E402
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
        self.assertGreater(corpus.log_likelihood(50, 10, 1000, 1000), 0)
        self.assertLess(corpus.log_likelihood(10, 50, 1000, 1000), 0)
        self.assertAlmostEqual(corpus.log_likelihood(10, 10, 1000, 1000), 0.0)


class GlyphTest(unittest.TestCase):
    def test_glyphs(self):
        self.assertEqual(ivtff.glyphs("qokchedy"), ["q", "o", "k", "ch", "e", "d", "y"])
        self.assertEqual(ivtff.glyphs("cthshckhy"), ["cth", "sh", "ckh", "y"])
        self.assertEqual(ivtff.glyphs("ch'o@185;l"), ["ch'", "o", "@185;", "l"])
        self.assertEqual(ivtff.glyphs("cy"), ["c", "y"])


class AffixTest(unittest.TestCase):
    WORDS = Counter({"qokedy": 3, "chedy": 2, "daiin": 4, "ol": 1, "s": 5})

    def test_prefix(self):
        tokens, types, whole = affix.affixes(self.WORDS, 2, suffix=False)
        self.assertEqual(tokens, Counter({"qo": 3, "che": 2, "da": 4, "ol": 1}))
        self.assertEqual(types["qo"], 1)
        self.assertEqual(whole, Counter({"ol": 1}))

    def test_suffix(self):
        tokens, _, _ = affix.affixes(self.WORDS, 3, suffix=True)
        self.assertEqual(tokens, Counter({"edy": 5, "iin": 4}))

    def test_positions(self):
        pos = affix.glyph_positions(self.WORDS)
        self.assertEqual(pos["q"], Counter({"語頭": 3}))
        self.assertEqual(pos["s"], Counter({"単独": 5}))
        self.assertEqual(pos["d"], Counter({"語中": 5, "語頭": 4}))

    def test_cross(self):
        table = affix.cross_table(self.WORDS, 1, 2)
        self.assertEqual(table[("q", "dy")], 3)
        self.assertEqual(table[("ch", "dy")], 2)
        self.assertNotIn(("o", "ol"), table)  # 3 字形未満は対象外


if __name__ == "__main__":
    unittest.main()

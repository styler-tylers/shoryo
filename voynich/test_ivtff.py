"""ivtff / word_freq / affix のテスト（python3 -m unittest discover voynich）。"""

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import affix  # noqa: E402
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_position  # noqa: E402
import vocab_shift  # noqa: E402
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


class LinePositionTest(unittest.TestCase):
    def setUp(self):
        raw = [
            "<%>pchor.daiin.chol.dam",  # 段落の最初の行
            "ychey.qokedy.otam",
            "sol.ar<$>",  # 2 語の行は比較に使わない
        ]
        lines = [ivtff.Line(ivtff.Page("f1r"), str(i), "+", "P0", r) for i, r in enumerate(raw)]
        self.tls = line_position.text_lines(lines, ivtff.Options())

    def test_text_lines(self):
        self.assertEqual([tl.paragraph_start for tl in self.tls], [True, False, False])
        self.assertEqual([tl.paragraph_end for tl in self.tls], [False, False, True])

    def test_collect(self):
        pos = line_position.collect(self.tls)
        self.assertEqual(pos.para_first, Counter({"pchor": 1}))
        self.assertEqual(pos.line_first_other, Counter({"ychey": 1}))
        self.assertEqual(pos.line_last_other, Counter({"dam": 1, "otam": 1}))
        self.assertEqual(pos.middle, Counter({"daiin": 1, "chol": 1, "qokedy": 1}))

    def test_glyph_helpers(self):
        words = Counter({"pchor": 2, "otam": 1})
        self.assertEqual(line_position.first_glyphs(words, 2), Counter({"pch": 2, "ot": 1}))
        self.assertEqual(line_position.last_glyphs(words), Counter({"r": 2, "m": 1}))

    def test_length_by_position(self):
        head, tail = line_position.length_by_position(self.tls, 1)
        # pchor(4) + ychey(4) + sol(3) 字形, 3 行
        self.assertEqual(head[0], [11, 3])
        self.assertEqual(tail[0], [3 + 4 + 2, 3])  # dam(3) + otam(4) + ar(2)


class VocabShiftTest(unittest.TestCase):
    def test_cosine(self):
        self.assertAlmostEqual(vocab_shift.cosine(Counter(a=1, b=1), Counter(a=2, b=2)), 1.0)
        self.assertEqual(vocab_shift.cosine(Counter(a=1), Counter(b=1)), 0.0)
        self.assertEqual(vocab_shift.cosine(Counter(), Counter(b=1)), 0.0)

    def test_glyph_bigrams(self):
        self.assertEqual(vocab_shift.glyph_bigrams(Counter({"qol": 2})),
                         Counter({"#q": 2, "qo": 2, "ol": 2, "l#": 2}))
        self.assertEqual(vocab_shift.glyph_bigrams(Counter({"chy": 1})),
                         Counter({"#ch": 1, "chy": 1, "y#": 1}))

    def test_folio_number(self):
        self.assertEqual(vocab_shift.folio_number("f86v3"), "86")
        self.assertEqual(vocab_shift.folio_number("f1r"), "1")

    def test_adjacency_test(self):
        # 隣り合うページだけが似ている並び: 実際の平均は並べ替えより大きくなるはず
        n = 10
        sim = [[1.0 if i == j else 0.9 if abs(i - j) == 1 else 0.1 for j in range(n)]
               for i in range(n)]
        obs, shuffled, p = vocab_shift.adjacency_test(sim, trials=200, seed=0)
        self.assertAlmostEqual(obs, 0.9)
        self.assertLess(shuffled, obs)
        self.assertLess(p, 0.05)

    def test_burstiness(self):
        page = ivtff.Page
        pages = [vocab_shift.PageText(page("f1r"), 0, Counter(x=10, y=1)),
                 vocab_shift.PageText(page("f1v"), 1, Counter(z=10, y=1)),
                 vocab_shift.PageText(page("f2r"), 2, Counter(z=10, y=1))]
        rows = vocab_shift.burstiness(pages, min_count=3)
        ratios = {word: ratio for ratio, word, *_ in rows}
        self.assertLess(ratios["x"], ratios["y"])  # x は 1 ページに集中
        self.assertGreater(ratios["y"], 1.0)  # y は全ページに散らばる（期待値より多いページに出る）


if __name__ == "__main__":
    unittest.main()

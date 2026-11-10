"""ivtff / word_freq / affix のテスト（python3 -m unittest discover voynich）。"""

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import affix  # noqa: E402
import anatomy_test  # noqa: E402
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_forms  # noqa: E402
import labels  # noqa: E402
import mismatch_test  # noqa: E402
import rater_aggregate  # noqa: E402
import line_position  # noqa: E402
import reorder  # noqa: E402
import self_citation  # noqa: E402
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


class LineFormsTest(unittest.TestCase):
    MIDDLE = Counter({"chedy": 5, "aiin": 4, "ol": 3, "ykeey": 2, "keey": 1, "daiin": 2})

    def test_strip(self):
        self.assertEqual(line_forms.strip_first("ychedy"), ("y", "chedy"))
        self.assertEqual(line_forms.strip_last("dam"), ("da", "m"))
        self.assertIsNone(line_forms.strip_first("y"))

    def test_stem_rate(self):
        first = Counter({"ychedy": 3, "ykeey": 1})
        # ychedy -> chedy（行中 5 回）は一致、ykeey -> keey（行中 1 回）は不一致
        self.assertEqual(line_forms.stem_rate(first, "y", self.MIDDLE, 2), (3, 4))

    def test_replace_rate(self):
        last = Counter({"dam": 2, "om": 1})
        self.assertEqual(line_forms.replace_rate(last, "m", "iin", self.MIDDLE, 2), (2, 3))
        self.assertEqual(line_forms.replace_rate(last, "m", "l", self.MIDDLE, 2), (1, 3))

    def test_stem_initials_and_only_at_start(self):
        first = Counter({"ychedy": 3, "ykeey": 1})
        self.assertEqual(line_forms.stem_initials(first, "y"), Counter({"ch": 3, "k": 1}))
        # ychedy は行中に無く、chedy は行中の語 → 行頭だけの語。ykeey は行中にもある
        self.assertEqual(line_forms.only_at_start(first, "y", self.MIDDLE, 2), (3, 4))


class CorpusTest(unittest.TestCase):
    def test_resolve_known_file(self):
        self.assertEqual(corpus.resolve_file(Path("IT2a-n.txt")), corpus.DATA_DIR / "IT2a-n.txt")
        self.assertEqual(corpus.resolve_file(Path("other.txt")), Path("other.txt"))


class ReorderTest(unittest.TestCase):
    @staticmethod
    def chain_sim(order):
        """order の順に隣どうしだけが似ている類似度行列。"""
        n = len(order)
        pos = {u: i for i, u in enumerate(order)}
        return [[1.0 if i == j else 0.9 if abs(pos[i] - pos[j]) == 1 else 0.1
                 for j in range(n)] for i in range(n)]

    def test_best_path_recovers_chain(self):
        import random
        true_order = [3, 0, 5, 1, 4, 2, 6]
        sim = self.chain_sim(true_order)
        found = reorder.best_path(sim, restarts=5, rng=random.Random(0))
        self.assertIn(found, (true_order, true_order[::-1]))

    def test_two_opt_improves(self):
        sim = self.chain_sim([0, 1, 2, 3, 4])
        bad = [0, 3, 2, 1, 4]
        better = reorder.two_opt(bad[:], sim)
        self.assertGreater(reorder.path_score(better, sim), reorder.path_score(bad, sim))

    def test_orient(self):
        self.assertEqual(reorder.orient([4, 3, 2, 1, 0]), [0, 1, 2, 3, 4])
        self.assertEqual(reorder.orient([0, 2, 1, 3]), [0, 2, 1, 3])

    def test_unit_key(self):
        page = ivtff.Page("f84v", {"Q": "M", "B": "1"})
        self.assertEqual(reorder.unit_key(page, "bifolio"), "M1")
        self.assertEqual(reorder.unit_key(page, "folio"), "f84")
        self.assertEqual(reorder.unit_key(page, "page"), "f84v")
        self.assertEqual(reorder.unit_key(ivtff.Page("f86v3"), "bifolio"), "f86")

    def test_bootstrap_keeps_size(self):
        import random
        words = Counter(daiin=5, ol=3, chedy=2)
        boot = reorder.bootstrap_words(words, random.Random(0))
        self.assertEqual(sum(boot.values()), 10)
        self.assertLessEqual(set(boot), set(words))

    def test_links(self):
        units = [reorder.Unit("A1", 0, [ivtff.Page("f1r")]), reorder.Unit("A2", 1, [ivtff.Page("f2r")])]
        sim = [[1.0, 0.1], [0.1, 1.0]]
        failed = reorder.apply_links(sim, units, [("f1r", "f2r"), ("f1r", "f9r")])
        self.assertAlmostEqual(sim[0][1], 0.1 + reorder.LINK_BONUS)
        self.assertEqual(len(failed), 1)


class SingulionTest(unittest.TestCase):
    def page_text(self, name, index, q="M", b="4"):
        return vocab_shift.PageText(ivtff.Page(name, {"Q": q, "B": b}), index, Counter())

    def test_plain_side(self):
        self.assertEqual(vocab_shift.plain_side("f78v"), (78, "v"))
        self.assertIsNone(vocab_shift.plain_side("f67r1"))

    def test_conjoint_and_facing(self):
        f78v, f81r = self.page_text("f78v", 7), self.page_text("f81r", 12)
        f79r = self.page_text("f79r", 8, b="5")
        self.assertTrue(vocab_shift.is_conjoint(f78v, f81r))
        self.assertTrue(vocab_shift.is_conjoint(f81r, f78v))
        self.assertFalse(vocab_shift.is_conjoint(self.page_text("f78r", 6), f81r))
        self.assertTrue(vocab_shift.is_current_facing(f78v, f79r))
        self.assertFalse(vocab_shift.is_current_facing(f78v, f81r))

    def test_mean_difference_test(self):
        p = vocab_shift.mean_difference_test([0.9] * 20, [0.1] * 20, trials=200, seed=0)
        self.assertLess(p, 0.01)

    def test_build_sheets_and_transitions(self):
        raw = [
            ("f1r", "A", "1", "daiin.ol"), ("f1v", "A", "1", "chedy"),
            ("f8r", "A", "1", "chedy"), ("f8v", "A", "1", "qokeedy.qokeedy"),
            ("f2r", "A", "2", "qokeedy"), ("f2v", "A", "2", "ol"),
            ("f7r", "A", "2", "ol"), ("f7v", "A", "2", "daiin"),
            ("f67r1", "I", "1", "otol"),
        ]
        lines = [ivtff.Line(ivtff.Page(n, {"Q": q, "B": b}), "1", "@", "P0", t) for n, q, b, t in raw]
        sheets, skipped = reorder.build_sheets(lines, ivtff.Options())
        self.assertEqual([sh.key for sh in sheets], ["1|8", "2|7"])
        self.assertEqual(len(skipped), 1)  # 折り込みの f67r1 は対象外
        trans = reorder.transition_matrix(sheets, "raw")
        # 1|8 の最後の頁 f8v（qokeedy）→ 2|7 の最初の頁 f2r（qokeedy）は同じ語
        self.assertAlmostEqual(trans[0][1], 1.0)
        # 2|7 の最後の頁 f7v（daiin）→ 1|8 の最初の頁 f1r（daiin ol）
        self.assertAlmostEqual(trans[1][0], 1 / 2 ** 0.5)
        self.assertAlmostEqual(reorder.sequence_score([0, 1], trans), 1.0)


class ResolvePageTest(unittest.TestCase):
    PAGES = {"f78v": None, "f67r": None, "f100v and 101r": None, "f85r (part) 86v (part) (part of 85-86 foldout)": None}

    def test_resolve(self):
        import spread
        self.assertEqual(spread.resolve_page(self.PAGES, "f78v"), "f78v")
        self.assertEqual(spread.resolve_page(self.PAGES, "f67r1"), "f67r")
        self.assertEqual(spread.resolve_page(self.PAGES, "f101r"), "f100v and 101r")
        self.assertEqual(spread.resolve_page(self.PAGES, "f86v3"),
                         "f85r (part) 86v (part) (part of 85-86 foldout)")
        self.assertIsNone(spread.resolve_page(self.PAGES, "f12r"))


class LabelsTest(unittest.TestCase):
    def test_stem(self):
        self.assertEqual(labels.stem("otaly"), "taly")
        self.assertEqual(labels.stem("qokeedy"), "keedy")
        self.assertEqual(labels.stem("ykal"), "kal")
        self.assertEqual(labels.stem("ol"), "ol")  # 短すぎる語はそのまま
        self.assertEqual(labels.stem("chedy"), "chedy")

    def test_collect_and_mention(self):
        page = ivtff.Page("f88r", {"I": "P"})
        lines = [
            ivtff.Line(page, "1", "@", "Lf", "otaly"),
            ivtff.Line(page, "2", "@", "Lf", "o"),  # 1 字形のラベルは除く
            ivtff.Line(page, "3", "@", "P0", "<%>daiin.taly.chol<$>"),
        ]
        lab, para, section = labels.collect(lines, ivtff.Options(), None, 2)
        self.assertEqual(lab["f88r"], [("otaly", "Lf")])
        assign = {"f88r": "f88r"}
        self.assertEqual(labels.mention_rate(["f88r"], assign, lab, para, False), (0, 1))
        self.assertEqual(labels.mention_rate(["f88r"], assign, lab, para, True), (1, 1))

    def test_circular_position(self):
        same = {"a": ["x", "y", "z", "w"], "b": ["x", "y", "z", "w"]}
        self.assertAlmostEqual(labels.circular_position_stat(same)[0], 0.0)
        opposite = {"a": ["x", "q", "r", "s"], "b": ["t", "u", "x", "v"]}
        self.assertAlmostEqual(labels.circular_position_stat(opposite)[0], 0.5)


class SelfCitationTest(unittest.TestCase):
    def test_distance(self):
        self.assertEqual(self_citation.distance("chedy", "chedy"), 0)
        self.assertEqual(self_citation.distance("chedy", "shedy"), 1)   # ch → sh
        self.assertEqual(self_citation.distance("chedy", "qochedy"), 2)  # 字形 2 つ追加
        self.assertEqual(self_citation.distance("daiin", "aiin"), 1)
        self.assertEqual(self_citation.best("okal", ["daiin", "okar", "ol"]), 1)

    def test_vertical_alignment_detects_copies(self):
        import random
        # 上の行の同じ位置の語を 1 字変えて写した頁（写しがあれば真上に偏る）
        rng = random.Random(0)
        vocab = ["daiin", "chol", "shey", "qokal", "otedy", "sar", "dor", "kchy", "lkam", "pchod"]
        pages = {}
        for n in range(6):
            lines = [rng.sample(vocab, 6)]
            for _ in range(10):
                prev = lines[-1]
                new = [w[:-1] + "x" if i % 2 == 0 else rng.choice(vocab) for i, w in enumerate(prev)]
                lines.append(new)
            pages[f"p{n}"] = lines
        obs, null, p, n = self_citation.vertical_alignment(pages, rng, 200)
        self.assertLess(obs, null)
        self.assertLess(p, 0.05)


class AnatomyTest(unittest.TestCase):
    def test_permutation_detects_grouping(self):
        import random
        # 型 X の頁どうしだけが似ている類似度行列
        labels = ["X"] * 6 + ["Y"] * 6
        sim = [[1.0 if i == j else (0.8 if labels[i] == labels[j] == "X" else 0.2) for j in range(12)]
               for i in range(12)]
        s, d, ns, nd, p = anatomy_test.permutation_test(labels, sim, lambda i, j: False, 500, random.Random(0))
        self.assertGreater(s, d)
        self.assertLess(p, 0.05)
        self.assertEqual(ns + nd, 66)

    def test_classification_file(self):
        classes = anatomy_test.load_classes(False)
        self.assertEqual(len(classes), 54)
        self.assertTrue(all(r["根"] in {"R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"} for r in classes.values()))
        self.assertTrue(all(r["葉"] in {"L0", "L1", "L2", "L3", "L4", "L5"} for r in classes.values()))


class MismatchTest(unittest.TestCase):
    def test_load_consistent(self):
        mism, roots, lang = mismatch_test.load()
        self.assertEqual(len(mism), 52)
        self.assertTrue(all(0 <= v <= 4 for v in mism.values()))
        self.assertTrue(set(mism) <= set(roots) and set(mism) <= set(lang))
        self.assertTrue(all(roots[p] != "R0" for p in mism))

    def test_perm_p(self):
        import random
        # 明らかな差は小さな p
        labels = ["x"] * 10 + ["y"] * 10
        vals = [1] * 10 + [0] * 10

        def stat(ls):
            return sum(v for v, l in zip(vals, ls) if l == "x") - sum(v for v, l in zip(vals, ls) if l == "y")

        p = mismatch_test.perm_p(stat(labels), stat, labels, 500, random.Random(0))
        self.assertLess(p, 0.01)


class RaterAggregateTest(unittest.TestCase):
    def test_fleiss_kappa(self):
        # 手計算: P̄ = 7/9, Pe = 41/81 → κ = 22/40
        k = rater_aggregate.fleiss_kappa([["a", "a", "a"], ["b", "b", "b"], ["a", "a", "b"]])
        self.assertAlmostEqual(k, 0.55)
        self.assertAlmostEqual(rater_aggregate.fleiss_kappa([["a", "a", "a"], ["b", "b", "b"]]), 1.0)


if __name__ == "__main__":
    unittest.main()

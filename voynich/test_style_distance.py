import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style_distance as sd  # noqa: E402


def rows(types, m=(0, 0, 0, 0)):
    return [{"根の型": t, **{it: str(x) for it, x in zip(sd.ITEMS, m)}} for t in types]


class StyleDistanceTest(unittest.TestCase):
    def test_tv(self):
        self.assertAlmostEqual(sd.tv([1, 0], [0, 1]), 1.0)
        self.assertAlmostEqual(sd.tv([0.5, 0.5], [0.5, 0.5]), 0.0)

    def test_mix_recovers_pure_sources(self):
        a = rows(["R6"] * 20)
        b = rows(["R4"] * 20)
        self.assertGreater(sd.mix_w_types(rows(["R6"] * 10), a, b), 0.9)
        self.assertLess(sd.mix_w_types(rows(["R4"] * 10), a, b), 0.1)
        self.assertAlmostEqual(sd.mix_w_types(rows(["R6"] * 5 + ["R4"] * 5), a, b), 0.5, delta=0.05)

    def test_mix_items(self):
        a = rows(["R4"] * 4, (1, 1, 1, 1))
        b = rows(["R4"] * 4, (0, 0, 0, 0))
        v = rows(["R4"] * 3, (1, 1, 1, 1)) + rows(["R4"], (0, 0, 0, 0))
        self.assertAlmostEqual(sd.mix_w_items(v, a, b), 0.75)


if __name__ == "__main__":
    unittest.main()

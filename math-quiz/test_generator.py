"""Unit test untuk generator.py.   Jalankan: python3 -m unittest -v"""
import operator
import random
import re
import unittest
from fractions import Fraction

import generator as g

OPS = {"<": operator.lt, ">": operator.gt, "≤": operator.le, "≥": operator.ge}
XS = [Fraction(i, 2) for i in range(-80, 81)]  # titik uji pertidaksamaan


def parse_option(opt):
    m = re.fullmatch(r"x (<|>|≤|≥) (−?\d+)", opt)
    assert m, opt
    return m.group(1), int(m.group(2).replace("−", "-"))


def answer_to_text(fr):
    return str(fr.numerator) if fr.denominator == 1 else f"{fr.numerator}/{fr.denominator}"


class GeneratorTests(unittest.TestCase):
    def verify(self, tag, q):
        self.assertTrue(len(q["prompt"]) > 8, tag)
        self.assertFalse(re.search(r"\b(None|nan|inf)\b|\?\?", q["prompt"]), f"{tag}: {q['prompt']}")
        self.assertTrue(q["steps"], tag)
        meta = q["meta"]

        if q["type"] == "input":
            # Oracle independen: hitung ulang dari ekspresi/persamaan
            if "expr" in meta:
                val = eval(meta["expr"], {"Fraction": Fraction})  # ekspresi buatan sendiri
                self.assertAlmostEqual(float(val), float(q["answer"]), places=9, msg=f"{tag}: {q['prompt']}")
            elif meta["kind"] == "linear":
                (a, b), (c, d) = meta["lhs"], meta["rhs"]
                x = q["answer"]
                self.assertEqual(a * x + b, c * x + d, f"{tag}: {q['prompt']}")
                self.assertEqual(x.denominator, 1, tag)
            else:
                self.fail(f"meta tidak dikenal: {meta}")

            # kunci diterima, jawaban salah ditolak
            ok = answer_to_text(q["answer"])
            self.assertEqual(g.check_answer(q, ok), "correct", f"{tag}: {ok}")
            bad = answer_to_text(q["answer"] + 1)
            self.assertEqual(g.check_answer(q, bad), "wrong", tag)

        else:  # pilihan ganda (pertidaksamaan)
            opts = q["options"]
            self.assertEqual(len(opts), 4, tag)
            self.assertEqual(len(set(opts)), 4, f"{tag}: opsi kembar")
            self.assertTrue(0 <= q["answer"] < 4, tag)
            a, b, sym, c = meta["a"], meta["b"], meta["sym"], meta["c"]

            def original(x):
                return OPS[sym](a * x + b, c)

            def option_truth(opt, x):
                s, k = parse_option(opt)
                return OPS[s](x, k)

            # opsi benar ekuivalen dengan pertidaksamaan asli
            for x in XS:
                self.assertEqual(original(x), option_truth(opts[q["answer"]], x), f"{tag}: {q['prompt']} x={x}")
            # setiap opsi salah memang berbeda penyelesaiannya
            for i, opt in enumerate(opts):
                if i != q["answer"]:
                    self.assertTrue(any(original(x) != option_truth(opt, x) for x in XS),
                                    f"{tag}: distraktor ekuivalen {opt}")
            self.assertEqual(g.check_answer(q, q["answer"]), "correct")
            self.assertEqual(g.check_answer(q, (q["answer"] + 1) % 4), "wrong")

    def test_semua_topik(self):
        for topic in g.TOPICS:
            for seed in range(300):
                qs = g.generate_set(topic, 10, random.Random(seed), choice_rate=0)
                self.assertEqual(len(qs), 10)
                self.assertEqual(len({q["prompt"] for q in qs}), 10, f"{topic}/seed{seed}: soal kembar")
                for i, q in enumerate(qs):
                    self.verify(f"{topic}/seed{seed}/#{i}", q)

    def test_konversi_pilihan_ganda(self):
        """Semua soal isian yang diubah jadi pilihan ganda: 4 opsi berbeda, tepat 1 benar."""
        n_choice = 0
        for topic in g.TOPICS:
            for seed in range(200):
                qs = g.generate_set(topic, 10, random.Random(seed), choice_rate=1)
                for i, q in enumerate(qs):
                    tag = f"{topic}/seed{seed}/#{i}"
                    n_choice += 1
                    self.assertEqual(q["type"], "choice", tag)
                    self.assertEqual(len(q["options"]), 4, tag)
                    self.assertEqual(len(set(q["options"])), 4, f"{tag}: opsi kembar {q['options']}")
                    # opsi benar = teks kunci (tanpa tambahan bentuk campuran "(= 1 {1/4})")
                    self.assertEqual(q["options"][q["answer"]], q["answer_text"].split(" (")[0], tag)
                    self.assertEqual(g.check_answer(q, q["answer"]), "correct", tag)
                    for j in range(4):
                        if j != q["answer"]:
                            self.assertEqual(g.check_answer(q, j), "wrong", tag)
                    view = g.public_view(q, "id")
                    self.assertNotIn("answer", view)
        self.assertGreater(n_choice, 1000)

    def test_format_soal_tanpa_hitunglah(self):
        for topic in g.TOPICS:
            for q in g.generate_set(topic, 10, random.Random(3)):
                self.assertNotIn("Hitunglah", q["prompt"])
                self.assertNotIn("Tentukan nilai", q["prompt"])
        q = g.generate_set("bilangan-bulat", 1, random.Random(1), choice_rate=0)[0]
        self.assertTrue(q["prompt"].endswith(" = ?"), q["prompt"])

    def test_seed_sama_hasil_sama(self):
        for topic in g.TOPICS:
            a = [q["prompt"] for q in g.generate_set(topic, 10, random.Random(5))]
            b = [q["prompt"] for q in g.generate_set(topic, 10, random.Random(5))]
            self.assertEqual(a, b)

    def test_public_view_tidak_membocorkan_kunci(self):
        for topic in g.TOPICS:
            q = g.generate_set(topic, 1, random.Random(1))[0]
            view = g.public_view(q, "abc")
            self.assertEqual(set(view) - {"options", "placeholder"}, {"id", "type", "prompt"})

    def test_parse_number(self):
        P = g.parse_number
        self.assertEqual(P("3"), (Fraction(3), "integer", True))
        self.assertEqual(P("-5"), (Fraction(-5), "integer", True))
        self.assertEqual(P("−5"), (Fraction(-5), "integer", True))   # tanda minus asli
        self.assertEqual(P("x = 4"), (Fraction(4), "integer", True))
        self.assertEqual(P("1/2"), (Fraction(1, 2), "fraction", True))
        self.assertEqual(P(" 2 / 4 "), (Fraction(1, 2), "fraction", False))
        self.assertEqual(P("0,5"), (Fraction(1, 2), "decimal", True))
        self.assertEqual(P("1 1/2"), (Fraction(3, 2), "mixed", True))
        for bad in ["", "abc", "1/0", "1 1/0", "3x", "--2", None, 5, "1/2/3"]:
            self.assertIsNone(P(bad), bad)

    def test_check_answer_status(self):
        q = {"type": "input", "answer": Fraction(1, 2), "require_simplest": True}
        self.assertEqual(g.check_answer(q, "1/2"), "correct")
        self.assertEqual(g.check_answer(q, "0,5"), "correct")
        self.assertEqual(g.check_answer(q, "2/4"), "not_simplified")
        self.assertEqual(g.check_answer(q, "1/3"), "wrong")
        self.assertEqual(g.check_answer(q, "halo"), "invalid")
        q["require_simplest"] = False
        self.assertEqual(g.check_answer(q, "2/4"), "correct")

        m = {"type": "input", "answer": Fraction(5, 4), "require_simplest": True}
        self.assertEqual(g.check_answer(m, "1 1/4"), "correct")
        self.assertEqual(g.check_answer(m, "5/4"), "correct")

        c = {"type": "choice", "options": list("abcd"), "answer": 2}
        self.assertEqual(g.check_answer(c, 2), "correct")
        self.assertEqual(g.check_answer(c, 1), "wrong")
        self.assertEqual(g.check_answer(c, 9), "invalid")
        self.assertEqual(g.check_answer(c, "2"), "invalid")
        self.assertEqual(g.check_answer(c, True), "invalid")


if __name__ == "__main__":
    unittest.main()

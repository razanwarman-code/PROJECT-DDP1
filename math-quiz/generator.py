"""Question generator + pengecek jawaban untuk web latihan matematika.

Hanya memakai pustaka standar Python.

Tampilan pecahan di soal memakai token "{pembilang/penyebut}", misalnya "{1/2}".
Frontend mengubah token itu menjadi pecahan bersusun.

Tingkat kesulitan naik otomatis dalam satu set soal: ~40% level 1, ~30% level 2,
~30% level 3.
"""
import random
import re
from fractions import Fraction
from math import gcd, lcm

MINUS = "−"  # tanda minus sebenarnya (U+2212)


# ---------------------------------------------------------------- helper tampilan
def s(n):
    """Bilangan bulat -> teks dengan tanda minus yang rapi."""
    return str(n).replace("-", MINUS)


def sp(n):
    """Seperti s(), tapi bilangan negatif diberi kurung: (−5)."""
    return f"({s(n)})" if n < 0 else s(n)


def tok(n, d):
    return f"{{{n}/{d}}}"


def ft(fr):
    return tok(fr.numerator, fr.denominator)


def fr_plain(fr):
    return s(fr.numerator) if fr.denominator == 1 else ft(fr)


def fr_text(fr):
    """Teks jawaban untuk pecahan positif; pecahan tak murni ditambah bentuk campuran."""
    if fr.denominator == 1:
        return s(fr.numerator)
    t = ft(fr)
    if fr.numerator > fr.denominator:
        w, r = divmod(fr.numerator, fr.denominator)
        t += f" (= {w} {tok(r, fr.denominator)})"
    return t


def _nonzero(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v


def _input_q(prompt, answer, answer_text, steps, meta, require_simplest=False,
             placeholder="Jawabanmu"):
    return {
        "type": "input",
        "prompt": prompt,
        "answer": answer,  # Fraction
        "answer_text": answer_text,
        "steps": steps,
        "require_simplest": require_simplest,
        "placeholder": placeholder,
        "meta": meta,  # dipakai unit test, tidak dikirim ke browser
    }


# ---------------------------------------------------------------- 1. bilangan bulat
def _int_q(prompt, ans, steps, expr):
    return _input_q(f"{prompt} = ?", Fraction(ans), s(ans), steps, {"expr": expr},
                    False, "Jawabanmu (contoh: -5)")


def q_integer(rng, level):
    if level == 1:
        op = rng.choice(["+", "−"])
        a, b = _nonzero(rng, -10, 10), _nonzero(rng, -10, 10)
    elif level == 2:
        op = rng.choice(["+", "−", "×"])
        if op == "×":
            a, b = _nonzero(rng, -9, 9), _nonzero(rng, -9, 9)
        else:
            a, b = _nonzero(rng, -25, 25), _nonzero(rng, -25, 25)
    else:
        op = rng.choice(["×", "÷", "mix"])
        a = b = None

    if op == "+":
        ans = a + b
        same = (a < 0) == (b < 0)
        why = ("Tanda sama, jadi nilai mutlaknya dijumlahkan dan tandanya dipertahankan."
               if same else
               "Tanda berbeda, jadi nilai mutlaknya dikurangkan dan tanda mengikuti "
               "bilangan yang nilai mutlaknya lebih besar.")
        return _int_q(f"{s(a)} + {sp(b)}", ans,
                      [why, f"{s(a)} + {sp(b)} = {s(ans)}"], f"({a}) + ({b})")

    if op == "−":
        ans = a - b
        steps = [f"Mengurangi sama dengan menambah lawannya: {s(a)} − {sp(b)} = {s(a)} + {sp(-b)}",
                 f"{s(a)} + {sp(-b)} = {s(ans)}"]
        return _int_q(f"{s(a)} − {sp(b)}", ans, steps, f"({a}) - ({b})")

    if op == "×":
        if level == 3:
            a, b = _nonzero(rng, -15, 15), _nonzero(rng, -12, 12)
        ans = a * b
        sign = "positif (tanda sama)" if (a < 0) == (b < 0) else "negatif (tanda berbeda)"
        steps = [f"Kalikan nilai mutlaknya: {abs(a)} × {abs(b)} = {abs(ans)}.",
                 f"Hasilnya {sign}: {s(ans)}."]
        return _int_q(f"{s(a)} × {sp(b)}", ans, steps, f"({a}) * ({b})")

    if op == "÷":
        b = _nonzero(rng, -12, 12)
        q = _nonzero(rng, -12, 12)
        a = b * q
        sign = "positif (tanda sama)" if (a < 0) == (b < 0) else "negatif (tanda berbeda)"
        steps = [f"Bagi nilai mutlaknya: {abs(a)} ÷ {abs(b)} = {abs(q)}.",
                 f"Hasilnya {sign}: {s(q)}."]
        return _int_q(f"{s(a)} ÷ {sp(b)}", q, steps, f"({a}) / ({b})")

    # op == "mix": a ± b × c  (urutan operasi)
    a = _nonzero(rng, -20, 20)
    b, c = _nonzero(rng, -9, 9), _nonzero(rng, -9, 9)
    sign2 = rng.choice(["+", "−"])
    bc = b * c
    ans = a + bc if sign2 == "+" else a - bc
    steps = [f"Kerjakan perkalian lebih dulu: {sp(b)} × {sp(c)} = {s(bc)}.",
             f"{s(a)} {sign2} {sp(bc)} = {s(ans)}."]
    py = "+" if sign2 == "+" else "-"
    return _int_q(f"{s(a)} {sign2} {sp(b)} × {sp(c)}", ans, steps, f"({a}) {py} ({b}) * ({c})")


# ---------------------------------------------------------------- 2. pecahan
LV = {1: (6, 3), 2: (10, 5), 3: (12, 9)}  # (penyebut maks, pengali maks)


def _proper(rng, max_den):
    """Pecahan murni sederhana, penyebut 2..max_den."""
    while True:
        d = rng.randint(2, max_den)
        n = rng.randint(1, d - 1)
        if gcd(n, d) == 1:
            return Fraction(n, d)


def _proper_den(rng, d):
    while True:
        n = rng.randint(1, d - 1)
        if gcd(n, d) == 1:
            return Fraction(n, d)


def _pair_diff(rng, level):
    """Dua pecahan murni dengan penyebut berbeda."""
    if level <= 2:
        d1 = rng.randint(2, 5)
        d2 = d1 * rng.randint(2, 3)
        return _proper_den(rng, d1), _proper_den(rng, d2)
    while True:
        a, b = _proper(rng, 10), _proper(rng, 10)
        if a.denominator != b.denominator:
            return a, b


def _simp(raw_n, raw_d, ans):
    if gcd(raw_n, raw_d) == 1:
        return []
    return [f"Sederhanakan {tok(raw_n, raw_d)} menjadi {fr_plain(ans)}."]


def _f_equiv(rng, level):
    max_den, max_k = LV[level]
    base = _proper(rng, max_den)
    k = rng.randint(2, max_k)
    n, d = base.numerator, base.denominator
    target = d * k
    steps = [f"Penyebut {d} dikali {k} menjadi {target}.",
             f"Pembilang juga dikali {k}: {n} × {k} = {n * k}."]
    return _input_q(f"Lengkapi pecahan senilai: {tok(n, d)} = {{?/{target}}}",
                    Fraction(n * k), s(n * k), steps,
                    {"expr": f"Fraction({n},{d}) * {target}"}, False, "Isi pembilangnya")


def _f_simplify(rng, level):
    max_den, max_k = LV[level]
    base = _proper(rng, max_den)
    k = rng.randint(2, max_k)
    n, d = base.numerator * k, base.denominator * k
    steps = [f"FPB dari {n} dan {d} adalah {k}.",
             f"{n} ÷ {k} = {base.numerator} dan {d} ÷ {k} = {base.denominator}."]
    return _input_q(f"Sederhanakan pecahan {tok(n, d)}", base, fr_text(base), steps,
                    {"expr": f"Fraction({n},{d})"}, True, "Contoh: 3/4")


def _f_add_same(rng, level):
    d = rng.randint(3, 8 if level == 1 else 12)
    while True:
        a, b = rng.randint(1, d - 1), rng.randint(1, d - 1)
        if level > 1 or a + b <= d:
            break
    ans = Fraction(a + b, d)
    steps = [f"Penyebut sama, jadi cukup jumlahkan pembilang: {a} + {b} = {a + b}.",
             f"Hasilnya {tok(a + b, d)}."] + _simp(a + b, d, ans)
    return _input_q(f"{tok(a, d)} + {tok(b, d)} = ?", ans, fr_text(ans), steps,
                    {"expr": f"Fraction({a},{d}) + Fraction({b},{d})"}, True, "Contoh: 3/4")


def _addsub(rng, level, sign):
    a, b = _pair_diff(rng, level)
    if sign == "−" and a < b:
        a, b = b, a
    L = lcm(a.denominator, b.denominator)
    a2 = a.numerator * (L // a.denominator)
    b2 = b.numerator * (L // b.denominator)
    raw_n = a2 + b2 if sign == "+" else a2 - b2
    ans = a + b if sign == "+" else a - b
    steps = [f"KPK dari {a.denominator} dan {b.denominator} adalah {L}.",
             f"{ft(a)} = {tok(a2, L)} dan {ft(b)} = {tok(b2, L)}.",
             f"{tok(a2, L)} {sign} {tok(b2, L)} = {tok(raw_n, L)}."] + _simp(raw_n, L, ans)
    py = "+" if sign == "+" else "-"
    expr = f"Fraction({a.numerator},{a.denominator}) {py} Fraction({b.numerator},{b.denominator})"
    return a, b, ans, steps, expr


def _f_add_diff(rng, level):
    a, b, ans, steps, expr = _addsub(rng, level, "+")
    return _input_q(f"{ft(a)} + {ft(b)} = ?", ans, fr_text(ans), steps,
                    {"expr": expr}, True, "Contoh: 3/4")


def _f_sub_diff(rng, level):
    a, b, ans, steps, expr = _addsub(rng, level, "−")
    return _input_q(f"{ft(a)} − {ft(b)} = ?", ans, fr_text(ans), steps,
                    {"expr": expr}, True, "Contoh: 3/4")


def _f_mul(rng, level):
    a, b = _proper(rng, LV[level][0]), _proper(rng, LV[level][0])
    raw_n, raw_d = a.numerator * b.numerator, a.denominator * b.denominator
    ans = a * b
    steps = [f"Kalikan pembilang: {a.numerator} × {b.numerator} = {raw_n}.",
             f"Kalikan penyebut: {a.denominator} × {b.denominator} = {raw_d}."] + _simp(raw_n, raw_d, ans)
    return _input_q(f"{ft(a)} × {ft(b)} = ?", ans, fr_text(ans), steps,
                    {"expr": f"Fraction({a.numerator},{a.denominator}) * Fraction({b.numerator},{b.denominator})"},
                    True, "Contoh: 3/4")


ADD_CTX = [
    lambda a, b: f"Ibu memakai {a} kg tepung untuk adonan dan {b} kg tepung untuk hiasan kue. Berapa kg tepung yang dipakai seluruhnya?",
    lambda a, b: f"Budi minum {a} liter air di pagi hari dan {b} liter di siang hari. Berapa liter air yang ia minum seluruhnya?",
    lambda a, b: f"Sebuah pita dipotong menjadi dua bagian, panjangnya {a} meter dan {b} meter. Berapa meter panjang pita semula?",
]
SUB_CTX = [
    lambda a, b: f"Rina punya {a} kg gula. Ia memakai {b} kg untuk membuat kue. Berapa kg gula yang tersisa?",
    lambda a, b: f"Sebuah tangki berisi {a} liter minyak. Sebanyak {b} liter dipakai. Berapa liter minyak yang tersisa?",
    lambda a, b: f"Tali sepanjang {a} meter dipotong {b} meter. Berapa meter sisa tali?",
]


def _f_word_add(rng, level):
    a, b, ans, steps, expr = _addsub(rng, level, "+")
    return _input_q(rng.choice(ADD_CTX)(ft(a), ft(b)), ans, fr_text(ans), steps,
                    {"expr": expr}, True, "Contoh: 3/4")


def _f_word_sub(rng, level):
    a, b, ans, steps, expr = _addsub(rng, level, "−")
    return _input_q(rng.choice(SUB_CTX)(ft(a), ft(b)), ans, fr_text(ans), steps,
                    {"expr": expr}, True, "Contoh: 3/4")


_FRACTION_POOLS = {
    1: [_f_equiv, _f_add_same, _f_simplify],
    2: [_f_add_diff, _f_sub_diff, _f_simplify, _f_equiv],
    3: [_f_add_diff, _f_sub_diff, _f_mul, _f_word_add, _f_word_sub],
}


def q_fraction(rng, level):
    return rng.choice(_FRACTION_POOLS[level])(rng, level)


# ---------------------------------------------------------------- 3. persamaan linear
def xterm(a):
    if a == 1:
        return "x"
    if a == -1:
        return MINUS + "x"
    return f"{s(a)}x"


def lin(a, b):
    """Teks 'ax + b' (b = 0 -> tanpa konstanta)."""
    t = xterm(a)
    if b > 0:
        t += f" + {b}"
    elif b < 0:
        t += f" − {abs(b)}"
    return t


def _move_const_step(b, new_rhs):
    if b > 0:
        return f"Kurangi kedua ruas dengan {b}: "
    return f"Tambahkan kedua ruas dengan {abs(b)}: "


def q_linear(rng, level):
    if level == 1:
        if rng.random() < 0.5:  # x + b = c
            x0 = _nonzero(rng, -9, 12)
            b = _nonzero(rng, -12, 12)
            c = x0 + b
            steps = [_move_const_step(b, c) + f"x = {s(c)} {'−' if b > 0 else '+'} {abs(b)} = {s(x0)}"]
            lhs, rhs = (1, b), (0, c)
            prompt = f"{lin(1, b)} = {s(c)}, maka x = ?"
        else:  # ax = c
            a = rng.randint(2, 9)
            x0 = _nonzero(rng, -9, 9)
            c = a * x0
            steps = [f"Bagi kedua ruas dengan {a}: x = {s(c)} ÷ {a} = {s(x0)}"]
            lhs, rhs = (a, 0), (0, c)
            prompt = f"{a}x = {s(c)}, maka x = ?"
    elif level == 2:
        a = rng.randint(2, 9)
        x0 = _nonzero(rng, -8, 10)
        b = _nonzero(rng, -15, 15)
        c = a * x0 + b
        steps = [_move_const_step(b, c) + f"{a}x = {s(c - b)}",
                 f"Bagi kedua ruas dengan {a}: x = {s(c - b)} ÷ {a} = {s(x0)}"]
        lhs, rhs = (a, b), (0, c)
        prompt = f"{lin(a, b)} = {s(c)}, maka x = ?"
    else:
        while True:
            a, c = _nonzero(rng, -9, 9), _nonzero(rng, -9, 9)
            if a != c:
                break
        x0 = _nonzero(rng, -8, 10)
        b = _nonzero(rng, -10, 10)
        d = a * x0 + b - c * x0
        steps = [f"Pindahkan suku x ke kiri dan konstanta ke kanan: {xterm(a - c)} = {s(d - b)}.",
                 f"Bagi kedua ruas dengan {s(a - c)}: x = {s(d - b)} ÷ {sp(a - c)} = {s(x0)}"]
        lhs, rhs = (a, b), (c, d)
        prompt = f"{lin(a, b)} = {lin(c, d)}, maka x = ?"
    return _input_q(prompt, Fraction(x0), f"x = {s(x0)}", steps,
                    {"kind": "linear", "lhs": lhs, "rhs": rhs}, False, "x = ?")


# ---------------------------------------------------------------- 4. pertidaksamaan
FLIP = {"<": ">", ">": "<", "≤": "≥", "≥": "≤"}
TOGGLE = {"<": "≤", "≤": "<", ">": "≥", "≥": ">"}


def q_inequality(rng, level):
    sym = rng.choice(list(FLIP))
    if level == 1:
        a = 1
    elif level == 2:
        a = rng.randint(2, 6)
    else:
        a = -rng.randint(2, 6) if rng.random() < 0.8 else rng.randint(2, 6)
    k = rng.randint(-8, 8)
    b = _nonzero(rng, -12, 12)
    c = a * k + b
    ans_sym = sym if a > 0 else FLIP[sym]

    correct = f"x {ans_sym} {s(k)}"
    wrong_k = -k if k != 0 else 1
    distractors = [f"x {FLIP[ans_sym]} {s(k)}",      # lupa membalik / salah arah
                   f"x {TOGGLE[ans_sym]} {s(k)}",    # salah sama dengan / tidak
                   f"x {ans_sym} {s(wrong_k)}"]      # salah hitung konstanta
    options = [correct] + distractors
    rng.shuffle(options)

    steps = [_move_const_step(b, c) + f"{xterm(a)} {sym} {s(c - b)}"]
    if a > 0 and a != 1:
        steps.append(f"Bagi kedua ruas dengan {a}: x {sym} {s(k)}")
    elif a < 0:
        steps.append(f"Bagi kedua ruas dengan {s(a)}. Karena dibagi bilangan NEGATIF, "
                     f"tanda pertidaksamaan dibalik: x {ans_sym} {s(k)}")
    return {
        "type": "choice",
        "prompt": f"{lin(a, b)} {sym} {s(c)}",
        "options": options,
        "answer": options.index(correct),
        "answer_text": correct,
        "steps": steps,
        "require_simplest": False,
        "placeholder": None,
        "meta": {"kind": "ineq", "a": a, "b": b, "sym": sym, "c": c},
    }


# ---------------------------------------------------------------- registry
TOPICS = {
    "bilangan-bulat": {
        "title": "Operasi Bilangan Bulat",
        "desc": "Tambah, kurang, kali, bagi dengan bilangan negatif",
        "fn": q_integer,
    },
    "pecahan": {
        "title": "Pecahan",
        "desc": "Pecahan senilai, penjumlahan, pengurangan, perkalian, soal cerita",
        "fn": q_fraction,
    },
    "persamaan-linear": {
        "title": "Persamaan Linear",
        "desc": "Mencari nilai x dari persamaan satu variabel",
        "fn": q_linear,
    },
    "pertidaksamaan": {
        "title": "Pertidaksamaan",
        "desc": "Menyelesaikan pertidaksamaan linear (awas tanda yang dibalik!)",
        "fn": q_inequality,
    },
}


def list_topics():
    return [{"id": k, "title": v["title"], "desc": v["desc"]} for k, v in TOPICS.items()]


def _opt_text(v, prefix=""):
    """Fraction -> teks opsi (pecahan memakai token {n/d})."""
    if v.denominator == 1:
        return prefix + s(int(v))
    return prefix + (MINUS if v < 0 else "") + tok(abs(v.numerator), v.denominator)


def _distractors(ans, allow_neg, rng):
    """3 jawaban salah yang masuk akal & berbeda dari kunci."""
    if ans.denominator == 1:
        n = int(ans)
        cands = [n + 1, n - 1, n + 2, n - 2, n + 10, n - 10, 2 * n, -n if allow_neg else n + 3]
        cands = [Fraction(c) for c in cands]
    else:
        p, d = ans.numerator, ans.denominator
        cands = [Fraction(p + 1, d), Fraction(p - 1, d), Fraction(p, d + 1), Fraction(p + 1, d + 1),
                 ans + 1, 1 / ans if ans else ans + 2]
        if d > 1:
            cands.append(Fraction(p, d - 1))
    ok = []
    for c in cands:
        if c != ans and c not in ok and (allow_neg or c > 0):
            ok.append(c)
    k = 2
    while len(ok) < 3:  # cadangan, hampir tidak pernah terpakai
        c = ans + k
        if c != ans and c not in ok:
            ok.append(c)
        k += 1
    return rng.sample(ok, 3)


def to_choice(q, rng):
    """Ubah soal isian (jawaban angka) menjadi pilihan ganda 4 opsi."""
    prefix = "x = " if q["answer_text"].startswith("x = ") else ""
    ans = q["answer"]
    allow_neg = "Fraction(" not in str(q["meta"].get("expr", ""))  # soal pecahan: jawaban tetap positif
    options_v = [ans] + _distractors(ans, allow_neg, rng)
    rng.shuffle(options_v)
    q["options"] = [_opt_text(v, prefix) for v in options_v]
    q["answer"] = options_v.index(ans)
    q["type"] = "choice"
    q["placeholder"] = None
    return q


def generate_set(topic, count=10, rng=None, choice_rate=0.3):
    """Buat satu set soal. Kesulitan naik bertahap (level 1 -> 3), prompt tidak kembar.

    choice_rate: peluang tiap soal isian diubah menjadi pilihan ganda."""
    rng = rng or random.Random()
    fn = TOPICS[topic]["fn"]
    out, seen = [], set()
    for i in range(count):
        level = 1 + (i * 3) // count
        for _ in range(30):
            q = fn(rng, level)
            if q["prompt"] not in seen:
                break
        seen.add(q["prompt"])
        if q["type"] == "input" and rng.random() < choice_rate:
            q = to_choice(q, rng)
        out.append(q)
    return out


def public_view(q, qid):
    """Bagian soal yang boleh dikirim ke browser (tanpa kunci jawaban)."""
    view = {"id": qid, "type": q["type"], "prompt": q["prompt"]}
    if q["type"] == "choice":
        view["options"] = q["options"]
    else:
        view["placeholder"] = q["placeholder"]
    return view


# ---------------------------------------------------------------- pengecek jawaban
_MIXED = re.compile(r"(-?)(\d+)\s+(\d+)\s*/\s*(\d+)")
_FRAC = re.compile(r"(-?)(\d+)\s*/\s*(\d+)")
_NUM = re.compile(r"(-?)(\d+)(?:\.(\d{1,4}))?")


def parse_number(text):
    """Teks siswa -> (nilai Fraction, bentuk, sudah_sederhana) atau None.

    Menerima: "3", "-5", "1/2", "2/4", "0,5", "0.5", "1 1/2", "x = 3".
    """
    if not isinstance(text, str) or len(text) > 40:
        return None
    t = text.strip().lower().replace(MINUS, "-").replace(",", ".")
    t = re.sub(r"^x\s*=\s*", "", t)

    m = _MIXED.fullmatch(t)
    if m:
        sign, w, n, d = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if d == 0:
            return None
        val = w + Fraction(n, d)
        return (-val if sign else val), "mixed", gcd(n, d) == 1

    m = _FRAC.fullmatch(t)
    if m:
        sign, n, d = m.group(1), int(m.group(2)), int(m.group(3))
        if d == 0:
            return None
        val = Fraction(n, d)
        return (-val if sign else val), "fraction", gcd(n, d) == 1

    m = _NUM.fullmatch(t)
    if m:
        val = Fraction(m.group(2) + ("." + m.group(3) if m.group(3) else ""))
        return (-val if m.group(1) else val), ("decimal" if m.group(3) else "integer"), True

    return None


def check_answer(q, user_answer):
    """Mengembalikan 'correct' | 'wrong' | 'not_simplified' | 'invalid'."""
    if q["type"] == "choice":
        if (isinstance(user_answer, bool) or not isinstance(user_answer, int)
                or not 0 <= user_answer < len(q["options"])):
            return "invalid"
        return "correct" if user_answer == q["answer"] else "wrong"

    parsed = parse_number(user_answer)
    if parsed is None:
        return "invalid"
    value, form, reduced = parsed
    if value != q["answer"]:
        return "wrong"
    if q["require_simplest"] and form in ("fraction", "mixed") and not reduced:
        return "not_simplified"
    return "correct"

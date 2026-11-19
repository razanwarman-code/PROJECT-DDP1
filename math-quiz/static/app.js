// Frontend latihan matematika. Semua soal & kunci jawaban datang dari server Python.

const $ = (id) => document.getElementById(id);
const TOTAL = 10;

const S = { topic: null, qs: [], i: 0, score: 0, locked: false, selected: null };

// ---------- util ----------
function esc(str) {
  return String(str).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// Teks soal -> HTML. Token {n/d} jadi pecahan bersusun.
function rich(text) {
  return esc(text).replace(
    /\{([^/{}]+)\/([^/{}]+)\}/g,
    (_, n, d) => `<span class="frac"><span class="num">${n}</span><span class="den">${d}</span></span>`
  );
}

function show(name) {
  for (const id of ["home", "quiz", "result"]) $(id).classList.toggle("hidden", id !== name);
}

function setTheme(t) {
  document.body.className = t || "";
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Terjadi kesalahan");
  return data;
}

// ---------- menu ----------
async function loadTopics() {
  const box = $("topics");
  try {
    const { topics } = await api("/api/topics");
    box.innerHTML = "";
    for (const t of topics) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "topic";
      b.innerHTML = `<span class="t-title">${esc(t.title)}</span><span class="t-desc">${esc(t.desc)}</span>`;
      b.onclick = () => startTopic(t);
      box.appendChild(b);
    }
  } catch (e) {
    box.textContent = "Gagal memuat topik. Pastikan server Python sedang berjalan.";
  }
}

async function startTopic(topic) {
  try {
    const data = await api(`/api/questions?topic=${encodeURIComponent(topic.id)}&count=${TOTAL}`);
    S.topic = topic;
    S.qs = data.questions;
    S.i = 0;
    S.score = 0;
    $("topic-title").textContent = topic.title;
    show("quiz");
    renderQuestion();
  } catch (e) {
    alert(e.message);
  }
}

function goMenu() {
  setTheme("");
  show("home");
}

// ---------- soal ----------
function hideFeedback() {
  const fb = $("feedback");
  fb.className = "feedback hidden";
  fb.innerHTML = "";
}

function showFeedback(kind, html) {
  const fb = $("feedback");
  fb.className = `feedback ${kind}`;
  fb.innerHTML = html;
}

function renderQuestion() {
  const q = S.qs[S.i];
  S.locked = false;
  S.selected = null;
  setTheme("");
  hideFeedback();

  $("progress-text").textContent = `Soal ${S.i + 1} dari ${S.qs.length}`;
  $("bar-fill").style.width = `${(S.i / S.qs.length) * 100}%`;
  $("prompt").innerHTML = rich(q.prompt);
  $("btn-check").classList.remove("hidden");
  $("btn-check").disabled = true;
  $("btn-next").classList.add("hidden");

  const area = $("answer-area");
  area.innerHTML = "";

  if (q.type === "choice") {
    q.options.forEach((opt, idx) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "option";
      b.innerHTML = rich(opt);
      b.onclick = () => {
        if (S.locked) return;
        S.selected = idx;
        [...area.children].forEach((c) => c.classList.remove("selected"));
        b.classList.add("selected");
        $("btn-check").disabled = false;
      };
      area.appendChild(b);
    });
  } else {
    const inp = document.createElement("input");
    inp.type = "text";
    inp.id = "answer-input";
    inp.autocomplete = "off";
    inp.spellcheck = false;
    inp.placeholder = q.placeholder || "Jawabanmu";
    inp.oninput = () => {
      $("btn-check").disabled = inp.value.trim() === "";
      if (!S.locked) hideFeedback();
    };
    area.appendChild(inp);
    inp.focus();
  }
}

async function check() {
  if (S.locked) return;
  const q = S.qs[S.i];
  const answer = q.type === "choice" ? S.selected : $("answer-input").value;
  if (answer === null || answer === "") return;

  $("btn-check").disabled = true;
  let res;
  try {
    res = await api("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: q.id, answer }),
    });
  } catch (e) {
    showFeedback("warn", esc(e.message));
    $("btn-check").disabled = false;
    return;
  }

  // Belum bisa dinilai: biarkan siswa memperbaiki
  if (res.status === "invalid") {
    showFeedback("warn", "Jawabanmu belum bisa dibaca. Contoh penulisan: <b>3</b>, <b>-5</b>, <b>1/2</b>, <b>0,5</b>, <b>1 1/2</b>.");
    $("btn-check").disabled = false;
    return;
  }
  if (res.status === "not_simplified") {
    showFeedback("warn", "<b>Hampir!</b> Nilainya sudah benar, tapi pecahannya belum disederhanakan. Coba sederhanakan lagi.");
    $("btn-check").disabled = false;
    return;
  }

  // Benar / salah -> kunci soal, ubah warna layar
  S.locked = true;
  if (res.correct) S.score++;
  setTheme(res.correct ? "correct" : "wrong");

  const steps = (res.steps || []).map((x) => `<li>${rich(x)}</li>`).join("");
  if (res.correct) {
    showFeedback("ok", `<div class="fb-title">Benar! 🎉</div>
      <details><summary>Lihat pembahasan</summary><ol>${steps}</ol></details>`);
  } else {
    showFeedback("bad", `<div class="fb-title">Belum tepat</div>
      Jawaban yang benar: <strong>${rich(res.answer_text)}</strong>
      <ol>${steps}</ol>`);
  }

  // Tandai pilihan ganda / kunci input
  if (q.type === "choice") {
    [...$("answer-area").children].forEach((c, idx) => {
      c.disabled = true;
      if (idx === S.selected) c.classList.add(res.correct ? "is-correct" : "is-wrong");
    });
  } else {
    $("answer-input").disabled = true;
  }

  $("btn-check").classList.add("hidden");
  const next = $("btn-next");
  next.textContent = S.i === S.qs.length - 1 ? "Lihat hasil" : "Lanjut";
  next.classList.remove("hidden");
  next.focus();
}

function next() {
  S.i++;
  if (S.i >= S.qs.length) return showResult();
  renderQuestion();
}

// ---------- hasil ----------
function showResult() {
  setTheme("");
  $("bar-fill").style.width = "100%";
  const total = S.qs.length;
  const ratio = S.score / total;
  $("result-score").textContent = `Skor: ${S.score} / ${total}`;
  $("result-emoji").textContent = ratio === 1 ? "🏆" : ratio >= 0.7 ? "🎉" : ratio >= 0.4 ? "💪" : "📘";
  $("result-msg").textContent =
    ratio === 1 ? "Sempurna! Semua benar."
    : ratio >= 0.7 ? "Bagus sekali! Tinggal sedikit lagi."
    : ratio >= 0.4 ? "Lumayan. Coba lagi untuk meningkatkan skormu."
    : "Jangan menyerah. Baca pembahasannya dan coba lagi.";
  show("result");
}

// ---------- event ----------
$("btn-check").onclick = check;
$("btn-next").onclick = next;
$("btn-back").onclick = goMenu;
$("btn-menu").onclick = goMenu;
$("btn-retry").onclick = () => startTopic(S.topic);

// Enter: periksa jawaban / lanjut ke soal berikutnya
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.target.tagName === "BUTTON") return;
  if ($("quiz").classList.contains("hidden")) return;
  if (S.locked) next();
  else if (!$("btn-check").disabled) check();
});

loadTopics();

// Frontend latihan matematika. Semua soal & kunci jawaban datang dari server Python.

const $ = (id) => document.getElementById(id);
const TOTAL = 10;

const S = { topic: null, qs: [], i: 0, score: 0, locked: false, selected: null, log: [], filter: "all", streak: 0,
  timer: null, run: 0, checking: false, timedOut: false, pendingTimeout: false };

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
  document.querySelector("main.card").classList.toggle("plain", name === "result"); // hasil: tanpa kartu putih
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
    S.log = [];
    S.filter = "all";
    S.streak = 0;
    S.run++;
    updateStreak(false);
    $("topic-title").textContent = topic.title;
    show("quiz");
    renderQuestion();
  } catch (e) {
    alert(e.message);
  }
}

function goMenu() {
  S.run++;
  stopTimer();
  setTheme("");
  show("home");
}

// ---------- streak ----------
// Tampil mulai ×2. Setiap bertambah: pulse kecil (skala naik lalu kembali normal).
function updateStreak(grew) {
  const el = $("streak");
  if (!el) return;
  if (S.streak < 2) {
    el.classList.add("hidden");
    return;
  }
  el.querySelector(".streak-num").textContent = `×${S.streak}`;
  el.classList.toggle("mega", S.streak >= 5); // streak 5+: desain bintang
  el.classList.remove("hidden");
  if (grew) {
    el.classList.remove("pulse");
    void el.offsetWidth; // restart animasi
    el.classList.add("pulse");
  }
}

// ---------- timer ----------
const TIME_LIMIT = 20;       // detik per soal
const TIME_LIMIT_LONG = 30;  // soal cerita (teks panjang)
const WARN_AT = 5;           // detik terakhir: lingkaran merah

function stopTimer() {
  if (S.timer) { clearInterval(S.timer); S.timer = null; }
}

function drawTimer(left, total) {
  const el = $("timer");
  if (!el) return;
  const low = left <= WARN_AT;
  const deg = (1 - left / total) * 360; // lingkaran terisi searah jarum jam
  el.style.background = `conic-gradient(${low ? "#ef4444" : "#fca5a5"} ${deg}deg, #fff 0)`;
  $("timer-n").textContent = Math.ceil(left);
  el.classList.toggle("low", low);
}

function startTimer(total) {
  stopTimer();
  const end = Date.now() + total * 1000;
  const tick = () => {
    const left = Math.max(0, end - Date.now()) / 1000;
    drawTimer(left, total);
    if (left <= 0) { stopTimer(); onTimeout(); }
  };
  S.timer = setInterval(tick, 50);
  tick();
}

let toastTimer = null;
function toast(msg) {
  const t = $("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 1800);
}

// Waktu habis: soal dicatat "tidak terjawab", lalu lanjut ke soal berikutnya
async function onTimeout() {
  if (S.locked || S.timedOut) return;
  if (S.checking) { S.pendingTimeout = true; return; } // jawabanmu sedang diperiksa, tunggu hasilnya
  S.timedOut = true;
  S.locked = true;
  stopTimer();
  const run = S.run;
  const q = S.qs[S.i];
  let info = {};
  try {
    info = await api("/api/reveal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: q.id }),
    });
  } catch (e) { /* tetap lanjut, tanpa kunci */ }
  if (run !== S.run) return; // pemain sudah kembali ke menu
  S.log.push({
    status: "timeout",
    correct: false,
    prompt: q.prompt,
    yourAnswer: null,
    correctAnswer: info.answer_text ? rich(info.answer_text) : "—",
    steps: info.steps || [],
  });
  S.streak = 0;
  updateStreak(false);
  toast("⏰ Waktu habis!");
  next();
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
  S.timedOut = false;
  S.pendingTimeout = false;
  S.checking = false;
  S.selected = null;
  setTheme("");
  hideFeedback();

  $("progress-text").textContent = `Soal ${S.i + 1} dari ${S.qs.length}`;
  $("bar-fill").style.width = `${(S.i / S.qs.length) * 100}%`;
  $("prompt").innerHTML = rich(q.prompt);
  $("prompt").classList.toggle("long", q.prompt.length > 45); // soal cerita: huruf lebih kecil
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
  startTimer(q.prompt.length > 45 ? TIME_LIMIT_LONG : TIME_LIMIT);
}

async function check() {
  if (S.locked) return;
  const q = S.qs[S.i];
  const answer = q.type === "choice" ? S.selected : $("answer-input").value;
  if (answer === null || answer === "") return;

  $("btn-check").disabled = true;
  let res;
  S.checking = true;
  try {
    res = await api("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: q.id, answer }),
    });
  } catch (e) {
    S.checking = false;
    if (S.pendingTimeout) { S.pendingTimeout = false; return onTimeout(); }
    showFeedback("warn", esc(e.message));
    $("btn-check").disabled = false;
    return;
  }
  S.checking = false;

  // Belum bisa dinilai: biarkan siswa memperbaiki
  if (S.pendingTimeout && (res.status === "invalid" || res.status === "not_simplified")) {
    S.pendingTimeout = false;
    return onTimeout(); // waktu habis saat jawaban belum bisa dinilai
  }
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
  S.pendingTimeout = false;
  stopTimer();
  if (res.correct) S.score++;
  S.streak = res.correct ? S.streak + 1 : 0;
  updateStreak(res.correct);
  S.log.push({
    status: res.correct ? "correct" : "wrong",
    prompt: q.prompt,
    yourAnswer: q.type === "choice" ? rich(q.options[answer]) : esc(String(answer).trim()),
    correctAnswer: rich(res.answer_text),
    steps: res.steps || [],
    correct: res.correct,
  });
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
      // pilihanmu: hijau jika benar, merah jika salah; jawaban yang benar selalu hijau
      if (idx === res.correct_index) c.classList.add("is-correct");
      else if (idx === S.selected) c.classList.add("is-wrong");
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
  stopTimer();
  setTheme("");
  $("bar-fill").style.width = "100%";
  const total = S.qs.length;
  const nOk = S.score;
  const nSkip = S.log.filter((x) => x.status === "timeout").length;
  const nBad = total - nOk - nSkip;
  $("rb-ok").textContent = `${nOk} Benar`;
  $("rb-bad").textContent = `${nBad} Salah`;
  $("rb-skip").textContent = `${nSkip} Tidak Terjawab`;
  $("ring").setAttribute("aria-label", `Skor ${nOk} dari ${total}`);
  S.filter = "all";
  show("result");
  window.scrollTo(0, 0);
  animateRing(nOk, nBad, nSkip, total);
  try { renderReview(); } catch (e) { console.error(e); }
}

// Donat: hijau = benar, merah = salah, kuning = tidak terjawab. Terisi searah jarum jam.
const RING_COLORS = { ok: "#038907", bad: "#ba3d3d", skip: "#d4c52a", track: "#e5e7eb" };
let ringRaf = null;

function drawRing(t, ok, bad, skip, total) {
  const limit = t * 360;
  const stops = [];
  let start = 0;
  for (const [n, color] of [[ok, RING_COLORS.ok], [bad, RING_COLORS.bad], [skip, RING_COLORS.skip]]) {
    if (!n) continue;
    const end = start + (n / total) * 360;
    const a = Math.min(start, limit), b = Math.min(end, limit);
    if (b > a) stops.push(`${color} ${a}deg ${b}deg`);
    start = end;
  }
  if (limit < 360) stops.push(`${RING_COLORS.track} ${limit}deg 360deg`);
  $("ring").style.background = `conic-gradient(${stops.join(", ")})`;
  $("ring-pct").textContent = `${Math.round(t * (ok / total) * 100)}%`;
}

function animateRing(ok, bad, skip, total) {
  cancelAnimationFrame(ringRaf);
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return drawRing(1, ok, bad, skip, total);
  const t0 = performance.now(), dur = 1000;
  const frame = (now) => {
    const x = Math.min(1, (now - t0) / dur);
    drawRing(1 - Math.pow(1 - x, 3), ok, bad, skip, total); // ease-out
    if (x < 1) ringRaf = requestAnimationFrame(frame);
  };
  ringRaf = requestAnimationFrame(frame);
}

// Review: semua soal beserta jawabanmu, jawaban benar, dan pembahasan
function renderReview() {
  const tabs = $("review-filter");
  const list = $("review-list");
  if (!tabs || !list) return; // index.html lama (cache): lewati review

  const count = (st) => S.log.filter((x) => x.status === st).length;
  tabs.innerHTML = "";
  [["all", "Semua", S.log.length], ["correct", "Benar", count("correct")],
   ["wrong", "Salah", count("wrong")], ["timeout", "Tidak Terjawab", count("timeout")]].forEach(([key, label, n]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `pill pill-${key}` + (S.filter === key ? " active" : "");
    b.innerHTML = `${label} <span class="pill-n">${n}</span>`;
    b.onclick = () => { S.filter = key; renderReview(); };
    tabs.appendChild(b);
  });

  list.innerHTML = "";
  const items = S.log
    .map((x, n) => ({ ...x, n }))
    .filter((x) => S.filter === "all" || x.status === S.filter);
  if (!items.length) {
    const empty = { wrong: "Tidak ada jawaban yang salah. Mantap! 🎉", correct: "Belum ada jawaban yang benar.",
                    timeout: "Semua soal terjawab tepat waktu. 👍" };
    list.innerHTML = `<p class="r-empty">${empty[S.filter] || ""}</p>`;
    return;
  }
  for (const x of items) {
    const el = document.createElement("article");
    el.className = `r-card ${{ correct: "r-ok", wrong: "r-bad", timeout: "r-timeout" }[x.status]}`;
    const steps = x.steps.map((t) => `<li>${rich(t)}</li>`).join("");
    el.innerHTML = `
      <div class="r-num">${x.n + 1}</div>
      <div class="r-body">
        <div class="r-prompt">${rich(x.prompt)}</div>
        ${x.status === "timeout"
          ? `<div class="r-ans skip"><span class="r-ico">⏰</span> Tidak dijawab (waktu habis)</div>`
          : `<div class="r-ans ${x.correct ? "ok" : "bad"}"><span class="r-ico">${x.correct ? "✓" : "✗"}</span> Jawabanmu: <strong>${x.yourAnswer}</strong></div>`}
        ${x.correct ? "" : `<div class="r-ans ok"><span class="r-ico">✓</span> Jawaban benar: <strong>${x.correctAnswer}</strong></div>`}
        <button type="button" class="r-toggle" aria-expanded="false">Lihat pembahasan <span class="chev">▾</span></button>
        <div class="r-steps hidden"><ol>${steps}</ol></div>
      </div>`;
    const btn = el.querySelector(".r-toggle");
    const box = el.querySelector(".r-steps");
    btn.onclick = () => {
      const open = box.classList.toggle("hidden") === false;
      btn.setAttribute("aria-expanded", open);
      btn.classList.toggle("open", open);
    };
    list.appendChild(el);
  }
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
  if ($("quiz").classList.contains("hidden") || S.timedOut) return;
  if (S.locked) next();
  else if (!$("btn-check").disabled) check();
});

loadTopics();

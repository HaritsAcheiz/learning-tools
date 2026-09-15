"""Server-rendered HTML pages: teal + white minimalist study desk.

Design tokens (approved): paper #FFFFFF, ink #0F2A2E, teal #0E7C7B,
teal-deep #0A5C5B, tint #E6F4F3, line #DCE9E8, muted #5A7573.
Display serif (Georgia) for headings, system sans for body and UI.
Single left-aligned column, quiet chrome, numbered study sequence.
"""
import html
import json

CSS = """
:root {
  --paper: #FFFFFF;
  --ink: #0F2A2E;
  --teal: #0E7C7B;
  --teal-deep: #0A5C5B;
  --tint: #E6F4F3;
  --line: #DCE9E8;
  --muted: #5A7573;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6;
}
.topbar {
  position: sticky; top: 0; background: var(--paper);
  border-bottom: 1px solid var(--line);
}
.topbar-inner {
  max-width: 68ch; margin: 0 auto; padding: 0.75rem 1.25rem;
  display: flex; align-items: baseline; gap: 1rem;
}
.wordmark {
  font-family: Georgia, "Times New Roman", serif; font-size: 1.25rem;
  color: var(--teal-deep); text-decoration: none;
}
.topbar-inner nav { margin-left: auto; font-size: 0.9rem; }
.topbar-inner nav a { color: var(--muted); }
main { max-width: 68ch; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
h1, h2, h3 { font-family: Georgia, "Times New Roman", serif; line-height: 1.25; }
h1 { font-size: 2rem; margin: 0 0 0.5rem; color: var(--teal-deep); }
.lede { color: var(--muted); margin-top: 0; }
a { color: var(--teal); }
a:hover { color: var(--teal-deep); }
:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }
.theme-list { list-style: none; margin: 1.5rem 0; padding: 0; border-top: 1px solid var(--line); }
.theme-list li { border-bottom: 1px solid var(--line); }
.theme-list a {
  display: flex; justify-content: space-between; gap: 1rem;
  padding: 0.9rem 0.25rem; text-decoration: none; color: var(--ink);
}
.theme-list a:hover { background: var(--tint); }
.theme-list .meta { color: var(--muted); font-size: 0.85rem; white-space: nowrap; }
button, .btn {
  font: inherit; cursor: pointer; border-radius: 6px;
  border: 1px solid var(--teal); background: var(--teal); color: #fff;
  padding: 0.5rem 1.1rem;
}
button:hover, .btn:hover { background: var(--teal-deep); border-color: var(--teal-deep); }
button.ghost { background: transparent; color: var(--teal-deep); }
button.ghost:hover { background: var(--tint); }
button:disabled { opacity: 0.55; cursor: default; }
input[type="text"], textarea, select {
  font: inherit; color: var(--ink); width: 100%;
  border: 1px solid var(--line); border-radius: 6px; padding: 0.5rem 0.75rem;
  background: #fff;
}
.step { display: grid; grid-template-columns: 3.5rem 1fr; gap: 1rem; margin-top: 2.5rem; }.step-num {
  font-family: Georgia, "Times New Roman", serif; font-size: 2.5rem;
  line-height: 1; color: var(--teal);
}
.steps { display: flex; gap: 0.25rem; margin: 1.5rem 0 0; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.steps a { padding: 0.5rem 0.9rem; text-decoration: none; color: var(--muted); border-radius: 8px 8px 0 0; }
.steps a:hover { background: var(--tint); color: var(--teal-deep); }
.steps a[aria-current="page"] { background: var(--tint); color: var(--teal-deep); font-weight: 600; }
.step h2 { margin: 0.4rem 0 0.75rem; font-size: 1.4rem; }
.step form { margin: 0.75rem 0; }
fieldset { border: 1px solid var(--line); border-radius: 8px; padding: 1rem; margin: 0 0 1rem; }
legend { padding: 0 0.5rem; font-weight: 600; }
label.opt { display: block; padding: 0.35rem 0; cursor: pointer; }
label.opt input { margin-right: 0.6rem; accent-color: var(--teal); }
.answer, .result, .notice {
  border-left: 3px solid var(--teal); background: var(--tint);
  padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin: 1rem 0;
}
.result .score { font-family: Georgia, "Times New Roman", serif; font-size: 1.5rem; color: var(--teal-deep); }
.cite { color: var(--muted); font-size: 0.85rem; }
.card { border: 1px solid var(--line); border-radius: 8px; padding: 1rem; margin: 0 0 1rem; }
.card .grade-row { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }
.empty { color: var(--muted); border: 1px dashed var(--line); border-radius: 8px; padding: 1.5rem; }
footer { max-width: 68ch; margin: 0 auto; padding: 1rem 1.25rem 2rem; color: var(--muted); font-size: 0.85rem; border-top: 1px solid var(--line); }
@media (max-width: 560px) {
  .step { grid-template-columns: 1fr; gap: 0; }
  .step-num { font-size: 1.75rem; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
button, .theme-list a { transition: background-color 120ms ease; }
"""


def shell(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang='id'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)} · learning-tools</title>"
        f"<style>{CSS}</style></head><body>"
        "<header class='topbar'><div class='topbar-inner'>"
        "<a class='wordmark' href='/'>learning-tools</a>"
        "<nav><a href='/'>Semua tema</a></nav>"
        "</div></header>"
        f"<main>{body}</main>"
        "<footer>Belajar efektif: baca, tanya, uji, ulangi terjadwal.</footer>"
        "</body></html>"
    )


def home(themes: list[dict]) -> str:
    if themes:
        rows = "".join(
            f"<li><a href='/themes/{html.escape(t['id'], quote=True)}'>"
            f"<span>{html.escape(t['name'])}</span>"
            f"<span class='meta'>{html.escape(t['kind'])}</span></a></li>"
            for t in themes
        )
        listing = f"<ul class='theme-list'>{rows}</ul>"
    else:
        listing = (
            "<div class='empty'><p>Belum ada materi. Taruh file PDF, DOCX, TXT, atau MD "
            "ke folder <code>learning_material</code>, lalu tekan Rescan.</p></div>"
        )
    body = (
        "<h1>Meja belajar</h1>"
        "<p class='lede'>Pilih satu tema, lalu ikuti alur baca, tanya, kuis, dan review terjadwal.</p>"
        "<form method='post' action='/rescan'><button type='submit'>Rescan materi</button></form>"
        f"{listing}"
    )
    return shell("Meja belajar", body)


def _ask_section(theme_id: str, answer: dict | None) -> str:
    out = (
        f"<form method='post' action='/themes/{html.escape(theme_id, quote=True)}/ask'>"
        "<label for='q'>Pertanyaan</label>"
        "<textarea id='q' name='question' rows='2' required "
        "placeholder='Contoh: Apa tujuan utama pedoman ini?'></textarea>"
        "<p><button type='submit'>Tanya materi</button></p></form>"
    )
    if answer:
        cites = ", ".join(f"[{i}]" for i in answer["cited"])
        out += (
            "<div class='answer'>"
            f"<p>{html.escape(answer['answer'])}</p>"
            f"<p class='cite'>Sumber: {html.escape(cites) if cites else '—'}</p>"
            "</div>"
        )
    return out


def _quiz_section(theme_id: str, items: list[dict]) -> str:
    if not items:
        return "<div class='empty'><p>Belum ada soal untuk tema ini.</p></div>"
    blocks = []
    for i, it in enumerate(items):
        hidden = html.escape(json.dumps(it), quote=True)
        opts = "".join(
            f"<label class='opt'><input type='radio' name='answer-{i}' value='{j}' required>"
            f"{html.escape(opt)}</label>"
            for j, opt in enumerate(it["options"])
        )
        blocks.append(
            f"<fieldset><legend>{html.escape(it['question'])}</legend>"
            f"<input type='hidden' name='item-{i}' value=\"{hidden}\">{opts}</fieldset>"
        )
    return (
        f"<form method='post' action='/themes/{html.escape(theme_id, quote=True)}/quiz'>"
        f"{''.join(blocks)}<p><button type='submit'>Periksa jawaban</button></p></form>"
    )


def _quiz_result(result: dict, items: list) -> str:
    pct = round(result["score"] * 100)
    rows = []
    for it, d in zip(items, result["details"]):
        mark = "Benar" if d["correct"] else "Kurang tepat"
        rows.append(
            f"<div class='card'><p><strong>{mark}.</strong> {html.escape(it.question)}</p>"
            f"<p>{html.escape(it.explanation)}</p></div>"
        )
    return (
        "<div class='result'>"
        f"<p class='score'>Skor {result['correct']}/{result['total']} ({pct}%)</p>"
        "<p>Yang kurang tepat tercatat sebagai konsep yang membingungkan — pelajari ulang, lalu coba lagi.</p>"
        "</div>" + "".join(rows)
    )


def _review_section(theme_id: str, due: list[dict], confused: list[dict]) -> str:
    parts = []
    if due:
        for c in due[:10]:
            parts.append(
                f"<div class='card'><p>{html.escape(c['front'])}</p>"
                f"<form method='post' action='/themes/{html.escape(theme_id, quote=True)}/review'>"
                f"<input type='hidden' name='card_id' value=\"{html.escape(c['id'], quote=True)}\">"
                "<div class='grade-row'>"
                "<button type='submit' name='quality' value='1'>Lupa</button>"
                "<button type='submit' name='quality' value='3' class='ghost'>Ragu</button>"
                "<button type='submit' name='quality' value='5' class='ghost'>Ingat</button>"
                "</div></form></div>"
            )
        if len(due) > 10:
            parts.append(f"<p class='cite'>+ {len(due) - 10} kartu lain menunggumu. Kerjakan 10 dulu.</p>")
    else:
        parts.append("<div class='empty'><p>Tidak ada kartu jatuh tempo. Semua aman — kembali besok.</p></div>")
    if confused:
        lis = "".join(
            f"<li>{html.escape(c['label'])} <span class='cite'>({c['count']}×)</span></li>"
            for c in confused
        )
        parts.append(f"<h3>Konsep yang membingungkan</h3><ul>{lis}</ul>")
    return "".join(parts)


STEPS = (("baca", "Baca", ""), ("tanya", "Tanya", "/tanya"),
         ("kuis", "Kuis", "/quiz"), ("review", "Review", "/review"))


def step_nav(theme_id: str, active: str) -> str:
    links = []
    for slug, label, suffix in STEPS:
        href = f"/themes/{theme_id}{suffix}"
        current = " aria-current='page'" if slug == active else ""
        links.append(
            f"<a href='{html.escape(href, quote=True)}'{current}>{label}</a>")
    return f"<nav class='steps' aria-label='Langkah belajar'>{''.join(links)}</nav>"


def theme_page(ctx: dict, active: str = "baca", answer: dict | None = None,
               quiz_result: dict | None = None, quiz_items: list | None = None,
               notice: str | None = None) -> str:
    name = html.escape(ctx["name"])
    notice_html = f"<div class='notice'><p>{html.escape(notice)}</p></div>" if notice else ""
    if active == "tanya":
        section = ("<section class='step'><div class='step-num'>2</div><div>"
                   "<h2>Tanya</h2>"
                   f"{_ask_section(ctx['theme_id'], answer)}"
                   "</div></section>")
    elif active == "kuis":
        quiz_block = _quiz_result(quiz_result, quiz_items or []) if quiz_result else _quiz_section(
            ctx["theme_id"], ctx["quiz_items"])
        section = ("<section class='step'><div class='step-num'>3</div><div>"
                   "<h2>Kuis</h2>"
                   f"{quiz_block}"
                   "</div></section>")
    elif active == "review":
        section = ("<section class='step'><div class='step-num'>4</div><div>"
                   "<h2>Review</h2>"
                   f"{_review_section(ctx['theme_id'], ctx['due'], ctx['confused'])}"
                   "</div></section>")
    else:
        section = ("<section class='step'><div class='step-num'>1</div><div>"
                   "<h2>Baca</h2>"
                   f"<p class='cite'>Mode: {html.escape(ctx['mode'])}</p>"
                   f"<p>{html.escape(ctx['summary'])}</p>"
                   "</div></section>")
    body = (
        f"<p><a href='/'>← Semua tema</a></p><h1>{name}</h1>"
        f"<p class='lede'>{ctx['chunks']} potongan materi · {len(ctx['due'])} kartu jatuh tempo</p>"
        f"{step_nav(ctx['theme_id'], active)}"
        f"{notice_html}"
        f"{section}"
    )
    return shell(name, body)

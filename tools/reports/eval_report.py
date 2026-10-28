"""Build a static HTML eval report from the main PC's eval results (hybrid and/or local).
Usage: python eval_report.py --hybrid path/to/results_hybrid.json --local path/to/results_local.json [--out eval_report.html]
Either file may be omitted. Percentages may be 0-1 or 0-100; latency in ms. Every number shown comes from the input files.
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path

CHART_JS = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
TARGET_RES = 80.0
TARGET_P95_S = 15.0
TARGET_FAST_S = 3.0


def pct(v):
    """Normalise a 0-1 or 0-100 value (or dict holding one) to 0-100."""
    if isinstance(v, dict):
        for k in ("accuracy", "intent_accuracy", "acc", "resolution_rate", "value"):
            if k in v:
                return pct(v[k])
        return None
    if not isinstance(v, (int, float)):
        return None
    return float(v) * 100 if v <= 1.0 else float(v)


def count(v):
    if isinstance(v, dict):
        for k in ("n", "count", "total", "support"):
            if isinstance(v.get(k), (int, float)):
                return int(v[k])
    return None


def norm_breakdown(d) -> dict:
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            p = pct(v)
            if p is not None:
                out[k] = {"pct": round(p, 1), "n": count(v)}
    elif isinstance(d, list):
        for row in d:
            if isinstance(row, dict):
                key = row.get("name") or row.get("language") or row.get("intent") or row.get("key")
                p = pct(row)
                if key and p is not None:
                    out[key] = {"pct": round(p, 1), "n": count(row)}
    return out


def load(path: str | None, label: str) -> dict | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        print(f"[warn] {label}: {p} not found, skipping")
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    lat = raw.get("latency_ms") or {}
    fails = raw.get("failures") or []
    return {
        "label": label,
        "file": p.name,
        "intent_accuracy": pct(raw.get("intent_accuracy")),
        "language_accuracy": pct(raw.get("language_accuracy")),
        "resolution_rate": pct(raw.get("resolution_rate")),
        "p50": lat.get("p50"), "p95": lat.get("p95"), "max": lat.get("max"),
        "per_language": norm_breakdown(raw.get("per_language")),
        "per_intent": norm_breakdown(raw.get("per_intent")),
        "model_used": raw.get("model_used"),
        "failures": fails if isinstance(fails, list) else [],
        "n": raw.get("n") or raw.get("total"),
    }


def fmt_pct(v):
    return "–" if v is None else f"{v:.1f}%"


def fmt_s(ms):
    return "–" if ms is None else f"{ms / 1000:.2f} s"


def kpi(label, value, target, ok):
    cls = "" if ok is None else ("ok" if ok else "bad")
    return (f'<div class="kpi {cls}"><small>{html.escape(label)}</small><b>{html.escape(value)}</b>'
            f'<span>{html.escape(target)}</span></div>')


def run_section(r: dict) -> str:
    res, p95 = r["resolution_rate"], r["p95"]
    k = "".join([
        kpi("Resolution rate", fmt_pct(res), f"target ≥ {TARGET_RES:.0f}%", None if res is None else res >= TARGET_RES),
        kpi("Intent accuracy", fmt_pct(r["intent_accuracy"]), "", None),
        kpi("Language detection", fmt_pct(r["language_accuracy"]), "", None),
        kpi("Latency p50", fmt_s(r["p50"]), f"goal < {TARGET_FAST_S:.0f} s", None if r["p50"] is None else r["p50"] / 1000 < TARGET_FAST_S),
        kpi("Latency p95", fmt_s(p95), f"limit < {TARGET_P95_S:.0f} s", None if p95 is None else p95 / 1000 < TARGET_P95_S),
        kpi("Latency max", fmt_s(r["max"]), "", None),
    ])
    models = r["model_used"]
    if isinstance(models, dict):
        models = ", ".join(f"{html.escape(str(m))}: {v}" for m, v in models.items())
    elif isinstance(models, list):
        models = ", ".join(html.escape(str(m)) for m in models)
    else:
        models = html.escape(str(models or "–"))
    return f"""
    <section><h2>{html.escape(r['label'])} mode <span>· {html.escape(r['file'])}{f" · {r['n']} questions" if r['n'] else ""}</span></h2>
      <div class="kpis">{k}</div>
      <p class="meta">Models used: {models}</p>
    </section>"""


def failures_table(runs: list[dict]) -> str:
    rows = []
    for r in runs:
        for f in r["failures"][:200]:
            if not isinstance(f, dict):
                f = {"text": str(f)}
            text = f.get("text") or f.get("query") or f.get("message") or ""
            exp = f.get("expected") or f.get("expected_intent") or f.get("gold") or ""
            got = f.get("got") or f.get("predicted") or f.get("intent") or f.get("predicted_intent") or ""
            lang = f.get("lang") or f.get("language") or ""
            extra = f.get("reason") or f.get("error") or ""
            rows.append(f"<tr><td>{html.escape(r['label'])}</td><td>{html.escape(str(lang))}</td>"
                        f"<td>{html.escape(str(text))}</td><td>{html.escape(str(exp))}</td>"
                        f"<td>{html.escape(str(got))}</td><td>{html.escape(str(extra))}</td></tr>")
    if not rows:
        return "<p class='meta'>No failures listed in the result files.</p>"
    return ("<table><thead><tr><th>Mode</th><th>Lang</th><th>Question</th><th>Expected</th><th>Got</th>"
            "<th>Note</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def build(runs: list[dict]) -> str:
    data = json.dumps([{k: r[k] for k in ("label", "per_language", "per_intent", "p50", "p95", "max",
                                          "resolution_rate", "intent_accuracy", "language_accuracy")} for r in runs])
    sources = ", ".join(html.escape(r["file"]) for r in runs)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hisab Kitab Eval Report</title>
<script src="{CHART_JS}"></script>
<style>
  :root {{ --bg:#0d1117; --panel:#161b22; --line:#2a3140; --text:#e6edf3; --muted:#8b949e; --ok:#3fb950; --bad:#f85149; --a:#4f9dff; --b:#d2a8ff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font:14px/1.5 system-ui,"Segoe UI","Noto Sans",sans-serif; }}
  .wrap {{ max-width:1200px; margin:0 auto; padding:28px 24px 60px; }}
  h1 {{ margin:0; font-size:24px; }} h1 + p {{ color:var(--muted); margin:4px 0 24px; }}
  h2 {{ font-size:17px; margin:28px 0 12px; }} h2 span {{ color:var(--muted); font-weight:400; font-size:13px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; }}
  .kpi small {{ display:block; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.05em; }}
  .kpi b {{ display:block; font-size:24px; font-variant-numeric:tabular-nums; margin:2px 0; }}
  .kpi span {{ color:var(--muted); font-size:12px; }}
  .kpi.ok {{ border-color:rgba(63,185,80,.5); }} .kpi.ok b {{ color:var(--ok); }}
  .kpi.bad {{ border-color:rgba(248,81,73,.5); }} .kpi.bad b {{ color:var(--bad); }}
  .meta {{ color:var(--muted); font-size:13px; }}
  .charts {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .chart {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; }}
  .chart.wide {{ grid-column:1 / -1; }}
  .chart h3 {{ margin:0 0 8px; font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
  table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:10px; overflow:hidden; font-size:13px; }}
  th,td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ color:var(--muted); font-weight:600; font-size:12px; }}
  @media (max-width:800px) {{ .charts {{ grid-template-columns:1fr; }} }}
</style></head>
<body><div class="wrap">
<h1>Hisab Kitab: Evaluation Report</h1>
<p>Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} from {sources}. Targets from the TCS brief: ≥ {TARGET_RES:.0f}% query resolution, &lt; {TARGET_P95_S:.0f} s response.</p>
{"".join(run_section(r) for r in runs)}
<h2>Breakdown</h2>
<div class="charts">
  <div class="chart"><h3>Accuracy by language</h3><canvas id="c-lang" height="220"></canvas></div>
  <div class="chart"><h3>Latency (seconds)</h3><canvas id="c-lat" height="220"></canvas></div>
  <div class="chart wide"><h3>Accuracy by intent</h3><div style="position:relative;height:560px"><canvas id="c-intent"></canvas></div></div>
  <div class="chart wide"><h3>Hybrid vs local</h3><canvas id="c-cmp" height="200"></canvas></div>
</div>
<h2>Failures</h2>
{failures_table(runs)}
</div>
<script>
const RUNS = {data};
const COLORS = ["#4f9dff", "#d2a8ff"];
Chart.defaults.color = "#8b949e"; Chart.defaults.borderColor = "#2a3140";
const keysOf = (f) => [...new Set(RUNS.flatMap((r) => Object.keys(r[f] || {{}})))];
const refLines = {{ id: "refLines", afterDatasetsDraw(chart) {{
  const {{ ctx, chartArea: a, scales }} = chart; const ax = chart.options.indexAxis === "y" ? scales.x : scales.y;
  (chart.options.plugins.refLines || []).forEach((l) => {{
    const p = ax.getPixelForValue(l.v); ctx.save(); ctx.strokeStyle = l.c; ctx.setLineDash([6, 4]); ctx.beginPath();
    if (chart.options.indexAxis === "y") {{ ctx.moveTo(p, a.top); ctx.lineTo(p, a.bottom); }} else {{ ctx.moveTo(a.left, p); ctx.lineTo(a.right, p); }}
    ctx.stroke(); ctx.fillStyle = l.c; ctx.font = "11px system-ui";
    chart.options.indexAxis === "y" ? ctx.fillText(l.t, p + 4, a.top + 10) : ctx.fillText(l.t, a.right - ctx.measureText(l.t).width - 4, p - 4);
    ctx.restore(); }}); }} }};
Chart.register(refLines);
function bars(id, field, horizontal) {{
  const keys = keysOf(field); if (!keys.length) {{ document.getElementById(id).replaceWith(Object.assign(document.createElement("p"), {{ className: "meta", textContent: "No " + field + " data in the result files." }})); return; }}
  new Chart(document.getElementById(id), {{ type: "bar",
    data: {{ labels: keys, datasets: RUNS.map((r, i) => ({{ label: r.label, backgroundColor: COLORS[i], maxBarThickness: 28, data: keys.map((k) => r[field]?.[k]?.pct ?? null) }})) }},
    options: {{ indexAxis: horizontal ? "y" : "x", responsive: true, maintainAspectRatio: !horizontal, scales: {{ [horizontal ? "x" : "y"]: {{ min: 0, max: 100, ticks: {{ callback: (v) => v + "%" }} }} }},
      plugins: {{ refLines: [{{ v: {TARGET_RES}, c: "#3fb950", t: "{TARGET_RES:.0f}% target" }}],
        tooltip: {{ callbacks: {{ label: (c) => c.dataset.label + ": " + c.raw + "%" + (RUNS[c.datasetIndex][field][c.label]?.n ? " (n=" + RUNS[c.datasetIndex][field][c.label].n + ")" : "") }} }} }} }} }});
}}
bars("c-lang", "per_language", false);
bars("c-intent", "per_intent", true);
new Chart(document.getElementById("c-lat"), {{ type: "bar",
  data: {{ labels: ["p50", "p95", "max"], datasets: RUNS.map((r, i) => ({{ label: r.label, backgroundColor: COLORS[i], maxBarThickness: 28, data: [r.p50, r.p95, r.max].map((v) => v == null ? null : v / 1000) }})) }},
  options: {{ scales: {{ y: {{ beginAtZero: true, suggestedMax: 16, ticks: {{ callback: (v) => v + " s" }} }} }},
    plugins: {{ refLines: [{{ v: {TARGET_P95_S}, c: "#f85149", t: "15 s limit" }}, {{ v: {TARGET_FAST_S}, c: "#3fb950", t: "3 s goal" }}] }} }} }});
new Chart(document.getElementById("c-cmp"), {{ type: "bar",
  data: {{ labels: ["Resolution rate", "Intent accuracy", "Language detection"], datasets: RUNS.map((r, i) => ({{ label: r.label, backgroundColor: COLORS[i], maxBarThickness: 28,
    data: [r.resolution_rate, r.intent_accuracy, r.language_accuracy].map((v) => v == null ? null : +v.toFixed(1)) }})) }},
  options: {{ indexAxis: "y", scales: {{ x: {{ min: 0, max: 100, ticks: {{ callback: (v) => v + "%" }} }} }}, plugins: {{ refLines: [{{ v: {TARGET_RES}, c: "#3fb950", t: "80%" }}] }} }} }});
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hybrid", default="results_hybrid.json")
    ap.add_argument("--local", default="results_local.json")
    ap.add_argument("--out", default=str(Path(__file__).parent / "eval_report.html"))
    a = ap.parse_args()
    runs = [r for r in (load(a.hybrid, "Hybrid"), load(a.local, "Local")) if r]
    if not runs:
        raise SystemExit("No result files found. Pass --hybrid and/or --local.")
    Path(a.out).write_text(build(runs), encoding="utf-8")
    print(f"wrote {a.out} from {[r['file'] for r in runs]}")


if __name__ == "__main__":
    main()

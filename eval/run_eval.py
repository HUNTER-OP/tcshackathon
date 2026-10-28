"""End-to-end evaluation of the Hisab Kitab pipeline on eval/queries.jsonl.

Usage (from D:\\Hisab_kitab):
    .venv\\Scripts\\python eval\\run_eval.py --mode hybrid
    .venv\\Scripts\\python eval\\run_eval.py --mode local --limit 50 --concurrency 2
"""
import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import bank_api  # noqa: E402
from app.pipeline import handle_message  # noqa: E402

QUERIES = Path(__file__).with_name("queries.jsonl")


def _get(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def _card_types(res) -> list[str]:
    out = []
    for c in _get(res, "cards", None) or []:
        t = _get(c, "type")
        if t:
            out.append(str(t))
    return out


def _resolved(q: dict, res, intent_ok: bool) -> bool:
    reply = (_get(res, "reply", "") or "").strip()
    if q["customer_id"] == "CUST004":
        return "consent" in _card_types(res) or "consent" in reply.lower()
    if not intent_ok or not reply:
        return False
    exp = q.get("expect_contains")
    return not exp or exp.lower() in reply.lower()


def _pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


async def _run_one(q: dict, mode: str, sem: asyncio.Semaphore) -> dict:
    async with sem:
        t0 = time.perf_counter()
        try:
            res = await handle_message(q["text"], q["customer_id"], mode=mode, history=[])
            err = None
        except Exception as e:  # count crashes as failures, keep going
            res, err = None, f"{type(e).__name__}: {e}"
        wall_ms = (time.perf_counter() - t0) * 1000
    if res is None:
        return {**q, "got_intent": None, "got_lang": None, "intent_ok": False, "lang_ok": False,
                "resolved": False, "latency_ms": wall_ms, "model_used": "error", "error": err, "reply": ""}
    got_intent = _get(res, "intent")
    got_lang = _get(res, "language")
    intent_ok = got_intent == q["intent"]
    # consent-blocked rows: the intent still has to be right, but resolution is about the refusal
    return {**q, "got_intent": got_intent, "got_lang": got_lang, "intent_ok": intent_ok,
            "lang_ok": got_lang == q["lang"], "resolved": _resolved(q, res, intent_ok),
            "latency_ms": float(_get(res, "latency_ms", wall_ms) or wall_ms),
            "model_used": _get(res, "model_used", "?"), "error": None,
            "reply": (_get(res, "reply", "") or "")[:300]}


def summarise(rows: list[dict], mode: str) -> dict:
    n = len(rows)
    lat = [r["latency_ms"] for r in rows]
    by_lang, by_intent = defaultdict(list), defaultdict(list)
    for r in rows:
        by_lang[r["lang"]].append(r)
        by_intent[r["intent"]].append(r)
    acc = lambda rs, k: round(sum(r[k] for r in rs) / len(rs), 4) if rs else 0.0  # noqa: E731
    return {
        "mode": mode, "n": n,
        "intent_accuracy": acc(rows, "intent_ok"),
        "language_accuracy": acc(rows, "lang_ok"),
        "resolution_rate": acc(rows, "resolved"),
        "latency_ms": {"p50": round(statistics.median(lat), 1) if lat else 0,
                       "p95": round(_pct(lat, 95), 1), "max": round(max(lat), 1) if lat else 0},
        "per_language": {l: {"n": len(rs), "intent_accuracy": acc(rs, "intent_ok"), "resolution_rate": acc(rs, "resolved")}
                         for l, rs in sorted(by_lang.items())},
        "per_intent": {i: {"n": len(rs), "intent_accuracy": acc(rs, "intent_ok")} for i, rs in sorted(by_intent.items())},
        "model_used": dict(Counter(r["model_used"] for r in rows)),
        "errors": sum(1 for r in rows if r["error"]),
        "failures": [{"text": r["text"], "lang": r["lang"], "expected": r["intent"], "got": r["got_intent"],
                      "resolved": r["resolved"], "error": r["error"], "reply": r["reply"]}
                     for r in rows if not r["resolved"] or not r["intent_ok"]],
    }


def print_table(s: dict) -> None:
    print(f"\n=== Hisab Kitab eval — mode={s['mode']}  n={s['n']} ===")
    print(f"intent accuracy   {s['intent_accuracy']:.1%}")
    print(f"language accuracy {s['language_accuracy']:.1%}")
    print(f"resolution rate   {s['resolution_rate']:.1%}   (target >= 80%)")
    L = s["latency_ms"]
    print(f"latency ms        p50 {L['p50']}  p95 {L['p95']}  max {L['max']}   (target p95 < 15000)")
    print(f"models            {s['model_used']}   errors {s['errors']}")
    print("\nlang       n   intent  resolved")
    for l, v in s["per_language"].items():
        print(f"{l:<10}{v['n']:>3}   {v['intent_accuracy']:>6.1%}  {v['resolution_rate']:>7.1%}")
    print("\nintent                 n   accuracy")
    for i, v in s["per_intent"].items():
        print(f"{i:<22}{v['n']:>3}   {v['intent_accuracy']:>6.1%}")
    if s["failures"]:
        print(f"\nfailures ({len(s['failures'])}, first 15):")
        for f in s["failures"][:15]:
            print(f"  [{f['lang']}] {f['text'][:60]!r}  expected={f['expected']} got={f['got']}"
                  + (f"  ERROR {f['error'][:60]}" if f["error"] else ""))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["hybrid", "local"], default="hybrid")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    qs = [json.loads(l) for l in QUERIES.read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.limit:
        # stratified: take an even slice from each language so small runs still cover all four
        by = defaultdict(list)
        for q in qs:
            by[q["lang"]].append(q)
        per = max(1, a.limit // len(by))
        qs = [q for l in sorted(by) for q in by[l][:per]][: a.limit]
    bank_api.conn()  # open the seeded DB once before fanning out
    sem = asyncio.Semaphore(max(1, a.concurrency))
    t0 = time.perf_counter()
    rows = await asyncio.gather(*(_run_one(q, a.mode, sem) for q in qs))
    s = summarise(list(rows), a.mode)
    s["wall_seconds"] = round(time.perf_counter() - t0, 1)
    out = Path(__file__).with_name(f"results_{a.mode}.json")
    out.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(s)
    print(f"\nwall time {s['wall_seconds']}s  ->  {out}")


if __name__ == "__main__":
    asyncio.run(main())

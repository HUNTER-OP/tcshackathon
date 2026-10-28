"""Full metrics report for the Hisab Kitab intent model + dataset summary.

Usage (from D:\\Hisab_kitab):  .venv\\Scripts\\python eval\\metrics_report.py
Prints everything to the terminal and writes eval/metrics/: classification reports, confusion matrices
(CSV + PNG), per-language accuracy, dataset summary (JSON + Markdown).

Test sets:
  A. internal split   data/processed/intent_test.jsonl  (12% held out by build_dataset.py, never trained on)
  B. held-out set     eval/queries.jsonl                (200 hand-written questions, 50 per language,
                                                          removed from training data by exact-match filter)
End-to-end pipeline numbers (resolution rate, latency) come from eval/run_eval.py -> eval/results_*.json.
"""
import csv
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score  # noqa: E402

from app.ml.intents import UNIFIED_INTENTS  # noqa: E402
from app.nlu.intent import IntentClassifier  # noqa: E402
from app.nlu.lang import detect_language  # noqa: E402

OUT = ROOT / "evaluation" / "metrics"
SHORT = {"check_balance": "balance", "transaction_history": "txn_hist", "spending_summary": "spending",
         "loan_eligibility": "loan_elig", "emi_calculation": "emi", "interest_rates": "rates",
         "loan_products": "loan_prod", "card_block": "card_blk", "card_activate": "card_act",
         "card_issue": "card_iss", "transfer_money": "transfer", "fees_charges": "fees", "atm_branch": "atm",
         "password_pin": "pin_pwd", "dispute_refund": "dispute", "human_agent": "human", "faq_general": "faq"}


def load(path: Path, label_key: str) -> list[dict]:
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    return [{"text": r["text"], "label": r[label_key], "lang": r.get("lang", "en")} for r in rows]


def print_matrix(cm, labels) -> str:
    names = [SHORT[l] for l in labels]
    w = max(len(n) for n in names) + 1
    head = " " * w + "".join(f"{n[:6]:>7}" for n in names)
    lines = [head] + [f"{names[i]:<{w}}" + "".join(f"{v:>7}" for v in row) for i, row in enumerate(cm)]
    return "\n".join(lines)


def heatmap(cm, labels, title: str, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = [SHORT[l] for l in labels]
    norm = cm / cm.sum(axis=1, keepdims=True).clip(min=1)
    fig, ax = plt.subplots(figsize=(11, 9.5), dpi=130)
    im = ax.imshow(norm, cmap="Greens", vmin=0, vmax=1)
    ax.set_xticks(range(len(names)), names, rotation=55, ha="right", fontsize=9)
    ax.set_yticks(range(len(names)), names, fontsize=9)
    for i in range(len(names)):
        for j in range(len(names)):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=7.5,
                        color="white" if norm[i, j] > 0.6 else "#1d3b28")
    ax.set_xlabel("Predicted intent")
    ax.set_ylabel("True intent")
    ax.set_title(title, fontsize=12, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.04, label="share of true class")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def evaluate(name: str, rows: list[dict], clf: IntentClassifier) -> dict:
    t0 = time.perf_counter()
    preds = [clf.predict(r["text"])[0] for r in rows]
    ms = (time.perf_counter() - t0) * 1000 / max(1, len(rows))
    gold = [r["label"] for r in rows]
    labels = [l for l in UNIFIED_INTENTS if l in set(gold) | set(preds)]
    rep_txt = classification_report(gold, preds, labels=labels, digits=3, zero_division=0)
    rep = classification_report(gold, preds, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(gold, preds, labels=labels)
    per_lang = {}
    for lang in ("en", "hi", "kn", "hinglish"):
        idx = [i for i, r in enumerate(rows) if r["lang"] == lang]
        if idx:
            per_lang[lang] = {"n": len(idx), "accuracy": round(accuracy_score([gold[i] for i in idx], [preds[i] for i in idx]), 4),
                              "macro_f1": round(f1_score([gold[i] for i in idx], [preds[i] for i in idx], average="macro", zero_division=0), 4)}
    lang_acc = None
    if name.startswith("heldout"):
        lang_acc = round(sum(detect_language(r["text"]) == r["lang"] for r in rows) / len(rows), 4)

    bar = "=" * 92
    print(f"\n{bar}\n{name.upper()}  ·  n={len(rows)}  ·  {ms:.1f} ms/query on {'GPU' if clf.kind == 'transformer' else 'CPU'}\n{bar}")
    print(f"accuracy {accuracy_score(gold, preds):.4f}   macro-F1 {rep['macro avg']['f1-score']:.4f}   weighted-F1 {rep['weighted avg']['f1-score']:.4f}"
          + (f"   language-detection accuracy {lang_acc:.4f}" if lang_acc is not None else ""))
    print("\nPer-language:")
    for k, v in per_lang.items():
        print(f"  {k:<9} n={v['n']:<5} accuracy {v['accuracy']:.4f}   macro-F1 {v['macro_f1']:.4f}")
    print("\nClassification report (precision / recall / F1 / support per intent):\n" + rep_txt)
    print("Confusion matrix (rows = true intent, columns = predicted):\n" + print_matrix(cm, labels))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}_classification_report.txt").write_text(rep_txt, encoding="utf-8")
    with open(OUT / f"{name}_confusion_matrix.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["true \\ predicted"] + labels)
        for lab, row in zip(labels, cm):
            w.writerow([lab] + list(row))
    heatmap(cm, labels, f"Hisab Kitab intent model — {name} (n={len(rows)}, acc {accuracy_score(gold, preds):.1%})",
            OUT / f"{name}_confusion_matrix.png")
    errors = [{"text": r["text"], "lang": r["lang"], "true": g, "pred": p} for r, g, p in zip(rows, gold, preds) if g != p]
    (OUT / f"{name}_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"n": len(rows), "accuracy": round(accuracy_score(gold, preds), 4), "macro_f1": round(rep["macro avg"]["f1-score"], 4),
            "weighted_f1": round(rep["weighted avg"]["f1-score"], 4), "per_language": per_lang, "language_detection_accuracy": lang_acc,
            "ms_per_query": round(ms, 2), "per_intent": {k: {m: round(v[m], 4) for m in ("precision", "recall", "f1-score", "support")}
                                                         for k, v in rep.items() if k in UNIFIED_INTENTS}}


def count_csv(p: Path) -> int:
    with open(p, encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def count_jsonl(p: Path) -> int:
    return sum(1 for l in open(p, encoding="utf-8") if l.strip())


def dataset_summary() -> dict:
    d = ROOT / "data"
    train = load(d / "processed" / "intent_train.jsonl", "label")
    test = load(d / "processed" / "intent_test.jsonl", "label")
    held = load(ROOT / "eval" / "queries.jsonl", "intent")
    files = [
        ("data/raw/banking77_train.csv", "Banking77 (PolyAI), CC-BY-4.0 — github.com/PolyAI-LDN/task-specific-datasets", count_csv(d / "raw" / "banking77_train.csv")),
        ("data/raw/banking77_test.csv", "Banking77 test split", count_csv(d / "raw" / "banking77_test.csv")),
        ("data/raw/bitext_banking.csv", "Bitext Retail Banking (Hugging Face), offensive variants removed", count_csv(d / "raw" / "bitext_banking.csv")),
        ("data/processed/llm_paraphrases.jsonl", "LLM paraphrases (Gemini / Groq / Ollama), app/ml/augment_llm.py", count_jsonl(d / "processed" / "llm_paraphrases.jsonl")),
        ("data/processed/intent_train.jsonl", "Final training set (app/ml/build_dataset.py)", len(train)),
        ("data/processed/intent_test.jsonl", "Internal test split (12%)", len(test)),
        ("eval/queries.jsonl", "Held-out test set, 50 per language", len(held)),
        ("data/logs/query_logs.txt", "Synthetic customer query logs (text format)", sum(1 for _ in open(d / "logs" / "query_logs.txt", encoding="utf-8"))),
        ("backend/app/products.json", "Bank products: rates, loans, fees, FAQ", 1),
    ]
    db = ROOT / "backend" / "hisab.db"
    bank = {}
    if db.exists():
        c = sqlite3.connect(db)
        bank = {t: c.execute(f"select count(*) from {t}").fetchone()[0] for t in ("customers", "accounts", "transactions", "cards", "loans")}
    s = {"files": [{"path": p, "description": desc, "rows": n} for p, desc, n in files],
         "train_by_language": dict(Counter(r["lang"] for r in train)),
         "train_by_intent": dict(Counter(r["label"] for r in train).most_common()),
         "heldout_by_language": dict(Counter(r["lang"] for r in held)),
         "synthetic_bank_db": bank}
    print("\n" + "=" * 92 + "\nDATASETS\n" + "=" * 92)
    for f in s["files"]:
        print(f"  {f['path']:<40} {f['rows']:>7}  {f['description']}")
    print(f"\n  training set by language: {s['train_by_language']}")
    print(f"  training set by intent:   {s['train_by_intent']}")
    print(f"  held-out set by language: {s['heldout_by_language']}")
    print(f"  synthetic bank (backend/hisab.db): {bank}")
    return s


def main() -> None:
    clf = IntentClassifier()
    meta = json.loads((Path(clf.path) / "metrics.json").read_text()) if (Path(clf.path) / "metrics.json").exists() else {}
    print(f"Model: {meta.get('base_model', clf.kind)} fine-tuned · trained in {meta.get('train_seconds', '?')} s · labels: {len(UNIFIED_INTENTS)} intents")
    data = ROOT / "data" / "processed"
    report = {
        "model": meta,
        "internal_split": evaluate("internal_split", load(data / "intent_test.jsonl", "label"), clf),
        "heldout_200": evaluate("heldout_200", load(ROOT / "eval" / "queries.jsonl", "intent"), clf),
        "datasets": dataset_summary(),
    }
    for mode in ("hybrid", "local"):
        p = ROOT / "eval" / f"results_{mode}.json"
        if p.exists():
            r = json.loads(p.read_text(encoding="utf-8"))
            report[f"end_to_end_{mode}"] = {k: r[k] for k in ("n", "intent_accuracy", "language_accuracy", "resolution_rate", "latency_ms")}
    print("\n" + "=" * 92 + "\nEND-TO-END PIPELINE (eval/run_eval.py, full chat flow incl. LLM)\n" + "=" * 92)
    for mode in ("hybrid", "local"):
        r = report.get(f"end_to_end_{mode}")
        if r:
            print(f"  {mode:<7} n={r['n']}  resolution {r['resolution_rate']}  intent acc {r['intent_accuracy']}  "
                  f"language acc {r['language_accuracy']}  latency ms {r['latency_ms']}")
    (OUT / "metrics_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT.relative_to(ROOT)}\\ (classification reports, confusion matrices CSV+PNG, errors, metrics_summary.json)")


if __name__ == "__main__":
    main()

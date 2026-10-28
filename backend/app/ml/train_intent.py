"""Fine-tune distilbert-base-multilingual-cased for unified intents on the local GPU."""
import json
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from ..config import settings
from .intents import UNIFIED_INTENTS

BASE = "distilbert-base-multilingual-cased"
DATA = Path(settings.data_dir) / "processed"


def _load(name):
    return [json.loads(line) for line in open(DATA / name, encoding="utf-8")]


def _oversample(rows, floor=600, seed=42):
    rng = random.Random(seed)
    by = {}
    for r in rows:
        by.setdefault(r["label"], []).append(r)
    out = []
    for lab, rs in by.items():
        out += rs
        while len([x for x in out if x["label"] == lab]) < floor:
            out += rng.sample(rs, min(len(rs), floor - len([x for x in out if x["label"] == lab])))
    rng.shuffle(out)
    return out


def main(epochs: int = 4, batch: int = 64, lr: float = 5e-5) -> dict:
    t0 = time.time()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    l2i = {l: i for i, l in enumerate(UNIFIED_INTENTS)}
    train, test = _oversample(_load("intent_train.jsonl")), _load("intent_test.jsonl")
    print("train", len(train), Counter(r["label"] for r in train).most_common(3))
    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, num_labels=len(UNIFIED_INTENTS), id2label=dict(enumerate(UNIFIED_INTENTS)), label2id=l2i).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * ((len(train) + batch - 1) // batch)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)

    def enc(rows):
        b = tok([r["text"] for r in rows], padding=True, truncation=True, max_length=64, return_tensors="pt").to(dev)
        return b, torch.tensor([l2i[r["label"]] for r in rows], device=dev)

    for ep in range(epochs):
        model.train()
        random.Random(ep).shuffle(train)
        for i in range(0, len(train), batch):
            x, y = enc(train[i:i + batch])
            with torch.autocast(dev, dtype=torch.bfloat16):
                loss = model(**x, labels=y).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
        print(f"epoch {ep + 1} loss {loss.item():.4f}")

    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(test), 256):
            x, _ = enc(test[i:i + 256])
            preds += model(**x).logits.argmax(-1).tolist()
    gold = [l2i[r["label"]] for r in test]
    per_lang = {}
    for lang in ("en", "hi", "kn", "hinglish"):
        idx = [k for k, r in enumerate(test) if r["lang"] == lang]
        if idx:
            per_lang[lang] = round(accuracy_score([gold[k] for k in idx], [preds[k] for k in idx]), 4)
    metrics = {"accuracy": round(accuracy_score(gold, preds), 4), "macro_f1": round(f1_score(gold, preds, average="macro"), 4),
               "per_language": per_lang, "n_test": len(test), "base_model": BASE, "train_seconds": round(time.time() - t0, 1)}
    out = Path(settings.model_dir)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out); tok.save_pretrained(out)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(metrics)
    return metrics


if __name__ == "__main__":
    main()

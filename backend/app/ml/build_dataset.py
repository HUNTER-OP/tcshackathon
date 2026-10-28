"""Merge Banking77 + Bitext (mapped to unified intents) + multilingual templates -> data/processed/intent_*.jsonl"""
import csv
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from ..config import settings
from .intents import UNIFIED_INTENTS, map_banking77, map_bitext
from .templates import FILL, PREFIX, SUFFIX, T

RAW = Path(settings.data_dir) / "raw"
OUT = Path(settings.data_dir) / "processed"
CAP_PER_INTENT_EN = 600  # keep source-heavy intents from drowning the rest


def template_examples(rng: random.Random, per_lang: int = 45) -> list[dict]:
    rows = []
    for intent, langs in T.items():
        for lang, phrases in langs.items():
            seen = set()
            combos = list(itertools.product(phrases, PREFIX[lang], SUFFIX[lang]))
            rng.shuffle(combos)
            for p, pre, suf in combos:
                f = FILL[lang]
                text = pre + p.format(amt=rng.choice(f["amt"]), loan=rng.choice(f["loan"]), days=rng.choice(f["days"])) + suf
                if rng.random() < 0.2 and lang in ("en", "hinglish"):
                    text = text.lower() if rng.random() < 0.5 else text.capitalize()
                if text not in seen:
                    seen.add(text)
                    rows.append({"text": text, "label": intent, "lang": lang})
                if len(seen) >= per_lang:
                    break
    return rows


def main(seed: int = 42) -> None:
    rng = random.Random(seed)
    src = []
    for name in ("banking77_train.csv", "banking77_test.csv"):
        for r in csv.DictReader(open(RAW / name, encoding="utf-8")):
            src.append({"text": r["text"], "label": map_banking77(r["category"]), "lang": "en"})
    for r in csv.DictReader(open(RAW / "bitext_banking.csv", encoding="utf-8")):
        src.append({"text": r["instruction"], "label": map_bitext(r["intent"]), "lang": "en"})
    rng.shuffle(src)
    per = Counter()
    capped = []
    for r in src:
        if per[r["label"]] < CAP_PER_INTENT_EN:
            per[r["label"]] += 1
            capped.append(r)
    rows = capped + template_examples(rng)
    rng.shuffle(rows)
    assert {r["label"] for r in rows} == set(UNIFIED_INTENTS)
    n_test = int(len(rows) * 0.12)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in (("intent_test.jsonl", rows[:n_test]), ("intent_train.jsonl", rows[n_test:])):
        with open(OUT / name, "w", encoding="utf-8") as fh:
            for r in part:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("rows", len(rows), "test", n_test, Counter(r["label"] for r in rows).most_common())
    print("langs", Counter(r["lang"] for r in rows))


if __name__ == "__main__":
    main()

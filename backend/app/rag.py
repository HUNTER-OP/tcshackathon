"""Small semantic FAQ index: products.json FAQs + deduplicated Bitext answers."""
import csv
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from .bank_api import PRODUCTS
from .config import settings
from .nlu.profanity import has_profanity

EMB_MODEL = "BAAI/bge-small-en-v1.5"
PER_INTENT = 4


def _clean(s: str) -> str:
    s = re.sub(r"\{\{[^}]+\}\}", "our support team", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _corpus() -> list[dict]:
    docs = [{"q": f["q"], "a": f["a"]} for f in PRODUCTS["faq"]]
    seen: dict[str, int] = {}
    path = Path(settings.data_dir) / "raw" / "bitext_banking.csv"
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if has_profanity(r["instruction"]) or has_profanity(r["response"]):
            continue
        if seen.get(r["intent"], 0) < PER_INTENT:
            seen[r["intent"]] = seen.get(r["intent"], 0) + 1
            docs.append({"q": r["instruction"], "a": _clean(r["response"])[:900]})
    return docs


@lru_cache(maxsize=1)
def _index():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMB_MODEL, device="cuda" if _cuda() else "cpu")
    docs = _corpus()
    emb = model.encode([d["q"] + " " + d["a"][:200] for d in docs], normalize_embeddings=True, batch_size=64)
    return model, docs, np.asarray(emb)


def _cuda() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


def search(query_en: str, k: int = 3) -> list[dict]:
    model, docs, emb = _index()
    q = model.encode([query_en], normalize_embeddings=True)[0]
    scores = emb @ q
    top = np.argsort(-scores)[:k]
    return [{"q": docs[i]["q"], "a": docs[i]["a"], "score": round(float(scores[i]), 3)} for i in top]

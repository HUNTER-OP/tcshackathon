import json
from functools import lru_cache
from pathlib import Path

from ..config import settings


class IntentClassifier:
    def __init__(self, path: str | None = None):
        self.path = Path(path or settings.model_dir)
        self.kind = "transformer" if (self.path / "config.json").exists() else "tfidf"
        if self.kind == "transformer":
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            self.torch = torch
            self.dev = "cuda" if torch.cuda.is_available() else "cpu"
            self.tok = AutoTokenizer.from_pretrained(self.path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.path).to(self.dev).eval()
            self.labels = [self.model.config.id2label[i] for i in range(self.model.config.num_labels)]
        else:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import make_pipeline
            rows = [json.loads(l) for l in open(Path(settings.data_dir) / "processed" / "intent_train.jsonl", encoding="utf-8")]
            self.model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2),
                                       LogisticRegression(max_iter=2000, C=5))
            self.model.fit([r["text"] for r in rows], [r["label"] for r in rows])

    def predict(self, text: str) -> tuple[str, float]:
        if self.kind == "tfidf":
            probs = self.model.predict_proba([text])[0]
            i = probs.argmax()
            return self.model.classes_[i], float(probs[i])
        with self.torch.no_grad():
            x = self.tok([text], truncation=True, max_length=64, return_tensors="pt").to(self.dev)
            p = self.model(**x).logits.softmax(-1)[0]
            i = int(p.argmax())
            return self.labels[i], float(p[i])


@lru_cache(maxsize=1)
def get_classifier() -> IntentClassifier:
    return IntentClassifier()

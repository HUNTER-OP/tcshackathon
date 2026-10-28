"""Remove rows containing profanity from every dataset file (Bitext includes deliberately offensive variants)."""
import csv
import json
from pathlib import Path

from ..config import settings
from ..nlu.profanity import has_profanity

DATA = Path(settings.data_dir)
ROOT = DATA.parent


def _csv(path: Path, fields: list[str]) -> tuple[int, int]:
    rows = list(csv.DictReader(open(path, encoding="utf-8", newline="")))
    keep = [r for r in rows if not any(has_profanity(r.get(f) or "") for f in fields)]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(keep)
    return len(rows), len(rows) - len(keep)


def _jsonl(path: Path) -> tuple[int, int]:
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    keep = [r for r in rows if not any(has_profanity(str(v)) for v in r.values() if isinstance(v, str))]
    with open(path, "w", encoding="utf-8") as fh:
        for r in keep:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows), len(rows) - len(keep)


def main() -> None:
    jobs = [
        (DATA / "raw" / "bitext_banking.csv", lambda p: _csv(p, ["instruction", "response"])),
        (DATA / "raw" / "banking77_train.csv", lambda p: _csv(p, ["text"])),
        (DATA / "raw" / "banking77_test.csv", lambda p: _csv(p, ["text"])),
        (DATA / "processed" / "llm_paraphrases.jsonl", _jsonl),
        (ROOT / "eval" / "queries.jsonl", _jsonl),
        (DATA / "logs" / "query_logs.jsonl", _jsonl),
    ]
    for path, fn in jobs:
        if path.exists():
            total, removed = fn(path)
            print(f"{path.relative_to(ROOT)}: removed {removed} of {total}")


if __name__ == "__main__":
    main()

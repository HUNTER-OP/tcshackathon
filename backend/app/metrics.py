import time
from collections import Counter, deque

_lat: deque = deque(maxlen=2000)
_recent: deque = deque(maxlen=30)
_c = {"total": 0, "resolved": 0, "handoffs": 0}
_by = {"intent": Counter(), "language": Counter(), "model": Counter()}


def record(r) -> None:
    _c["total"] += 1
    _c["handoffs"] += 1 if r.handoff else 0
    _c["resolved"] += 1 if (r.reply and not r.handoff) else 0
    _lat.append(r.latency_ms)
    _by["intent"][r.intent] += 1
    _by["language"][r.language] += 1
    _by["model"][r.model_used.split(":")[0]] += 1
    _recent.appendleft({"t": time.strftime("%H:%M:%S"), "intent": r.intent, "language": r.language,
                        "latency_ms": r.latency_ms, "model_used": r.model_used, "message": r.redacted_text[:80]})


def snapshot() -> dict:
    lat = sorted(_lat)
    p95 = lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else 0
    return {**_c, "avg_latency_ms": round(sum(lat) / len(lat)) if lat else 0, "p95_latency_ms": p95,
            "by_intent": dict(_by["intent"]), "by_language": dict(_by["language"]),
            "by_model": dict(_by["model"]), "recent": list(_recent)}


def reset() -> None:
    _lat.clear()
    _recent.clear()
    for k in _c:
        _c[k] = 0
    for c in _by.values():
        c.clear()

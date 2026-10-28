import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "").strip())
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    xai_api_key: str = field(default_factory=lambda: os.getenv("XAI_API_KEY", os.getenv("GROK_API_KEY", "")).strip())
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "8"))
    local_timeout_s: float = float(os.getenv("LOCAL_TIMEOUT_S", "12"))
    db_path: str = str(ROOT / "backend" / "hisab.db")
    model_dir: str = str(ROOT / "models" / "intent")
    data_dir: str = str(ROOT / "data")


settings = Settings()

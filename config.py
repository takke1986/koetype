"""設定・専門用語の読み書き。~/.aquavoice/ に保存する。"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".aquavoice"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
TERMS_FILE = CONFIG_DIR / "terms.json"


@dataclass
class Settings:
    claude_postprocess: bool = False
    anthropic_api_key: str = ""
    claude_provider: str = "anthropic"  # "anthropic" or "bedrock"
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    vad_threshold: float = 0.5
    min_silence_ms: int = 800


def _ensure() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    _ensure()
    if not SETTINGS_FILE.exists():
        return Settings()
    data = json.loads(SETTINGS_FILE.read_text())
    valid = {k: v for k, v in data.items() if k in Settings.__dataclass_fields__}
    return Settings(**valid)


def save_settings(s: Settings) -> None:
    _ensure()
    SETTINGS_FILE.write_text(json.dumps(asdict(s), ensure_ascii=False, indent=2))


def load_terms() -> dict[str, str]:
    _ensure()
    if not TERMS_FILE.exists():
        return {}
    return json.loads(TERMS_FILE.read_text())


def save_terms(terms: dict[str, str]) -> None:
    _ensure()
    TERMS_FILE.write_text(json.dumps(terms, ensure_ascii=False, indent=2))


def apply_terms(text: str, terms: dict[str, str]) -> str:
    for wrong, correct in terms.items():
        text = text.replace(wrong, correct)
    return text

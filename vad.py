"""Silero-VAD による音声区間検出と幻覚フィルター。"""

import collections
import unicodedata
from typing import Optional

import numpy as np
import torch
from silero_vad import VADIterator, load_silero_vad

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 512
PRE_BUFFER_CHUNKS = 10   # 発話前の約320msを保持
MIN_SPEECH_SEC = 0.5     # これより短い発話は無視

HALLUCINATIONS: frozenset[str] = frozenset({
    "thank you", "thanks", "thank you very much",
    "thank you for watching", "you", "bye", "bye bye",
    "ありがとうございました", "ありがとうございます",
    "ご視聴ありがとうございました", "字幕",
})

# 許可するUnicodeブロック（日本語・英語・記号のみ）
_ALLOWED_SCRIPTS = {"HIRAGANA", "KATAKANA", "CJK", "LATIN", "DIGIT", "PUNCTUATION", "SPACE"}


def _script(char: str) -> str:
    """文字のUnicodeスクリプト種別を大まかに返す。"""
    name = unicodedata.name(char, "")
    if "HIRAGANA" in name:
        return "HIRAGANA"
    if "KATAKANA" in name:
        return "KATAKANA"
    if "CJK" in name:
        return "CJK"
    if "LATIN" in name:
        return "LATIN"
    cat = unicodedata.category(char)
    if cat.startswith("N"):
        return "DIGIT"
    if cat.startswith("P") or cat.startswith("S"):
        return "PUNCTUATION"
    if cat.startswith("Z") or char in " \t\n":
        return "SPACE"
    return "OTHER"


def _has_foreign_script(text: str, threshold: float = 0.3) -> bool:
    """日本語・英語以外の文字が threshold 割以上なら True。"""
    if not text:
        return False
    other = sum(1 for c in text if _script(c) == "OTHER")
    return other / len(text) >= threshold


def is_hallucination(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized in HALLUCINATIONS:
        return True
    if _has_foreign_script(normalized):
        print(f"[VAD] 外国語スクリプト検出、スキップ: {repr(text)}")
        return True
    return False


class VADProcessor:
    def __init__(self, threshold: float = 0.5, min_silence_ms: int = 800) -> None:
        model = load_silero_vad()
        self._vad = VADIterator(
            model,
            threshold=threshold,
            sampling_rate=SAMPLE_RATE,
            min_silence_duration_ms=min_silence_ms,
            speech_pad_ms=100,
        )
        self._pre: collections.deque[np.ndarray] = collections.deque(maxlen=PRE_BUFFER_CHUNKS)
        self._buf: list[float] = []
        self._speaking = False

    @property
    def speaking(self) -> bool:
        return self._speaking

    def process(self, chunk: np.ndarray) -> tuple[Optional[bool], Optional[np.ndarray]]:
        """
        Returns:
            speaking_changed: True=発話開始, False=発話終了, None=変化なし
            audio: 発話終了時に音声データ、それ以外は None
        """
        tensor = torch.from_numpy(chunk.astype(np.float32))
        result = self._vad(tensor)

        speaking_changed: Optional[bool] = None
        audio: Optional[np.ndarray] = None

        if result:
            if "start" in result and not self._speaking:
                self._speaking = True
                speaking_changed = True
                for pre in self._pre:
                    self._buf.extend(pre.tolist())
                self._buf.extend(chunk.tolist())
            elif "end" in result and self._speaking:
                self._buf.extend(chunk.tolist())
                self._speaking = False
                speaking_changed = False
                if len(self._buf) >= SAMPLE_RATE * MIN_SPEECH_SEC:
                    audio = np.array(self._buf, dtype=np.float32)
                self._buf = []
        elif self._speaking:
            self._buf.extend(chunk.tolist())
        else:
            self._pre.append(chunk.copy())

        return speaking_changed, audio

    def reset(self) -> None:
        self._vad.reset_states()
        self._pre.clear()
        self._buf = []
        self._speaking = False

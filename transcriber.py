"""Cohere Transcribe モデルの推論。HuggingFace キャッシュを共有する。"""

import numpy as np
import torch
from transformers import AutoProcessor, pipeline

MODEL_ID = "CohereLabs/cohere-transcribe-03-2026"
LANGUAGE = "ja"


def _device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class Transcriber:
    def __init__(self) -> None:
        device = _device()
        print(f"[Transcriber] device={device}")
        self._pipe = pipeline(
            "automatic-speech-recognition",
            model=MODEL_ID,
            device=device,
            dtype=torch.float16,
        )
        # 日本語を強制指定（アラビア語等の誤認識を防ぐ）
        processor = AutoProcessor.from_pretrained(MODEL_ID)
        self._forced_decoder_ids = processor.get_decoder_prompt_ids(language=LANGUAGE)
        print(f"[Transcriber] language={LANGUAGE}, ready.")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        result = self._pipe(
            {"array": audio.astype(np.float32), "sampling_rate": sample_rate},
            generate_kwargs={"forced_decoder_ids": self._forced_decoder_ids},
        )
        return result["text"].strip()

"""Whisper transcription via stable-ts (word-level timestamps)."""

from __future__ import annotations
from typing import Callable


def transcribe(
    vocal_path: str,
    log: Callable[[str], None] = print,
    language: str | None = None,
) -> list[dict]:
    """
    Returns a list of segments:
        [{"text": str, "start": float, "end": float,
          "words": [{"word": str, "start": float, "end": float}, ...]}, ...]
    """
    import stable_whisper

    log("Caricamento modello Whisper medium — prima esecuzione: download ~1.5 GB...")
    model = stable_whisper.load_model("medium")
    log("Modello caricato. Inizio trascrizione...")

    result = model.transcribe(
        vocal_path,
        word_timestamps=True,
        language=language,
        fp16=_cuda_available(),
        verbose=False,
    )

    segments: list[dict] = []
    for seg in result.segments:
        words: list[dict] = []
        for w in (seg.words or []):
            word_text = w.word.strip()
            if not word_text:
                continue
            words.append({
                "word":  word_text,
                "start": float(w.start),
                "end":   float(w.end),
            })
        if not words:
            continue
        segments.append({
            "text":  seg.text.strip(),
            "start": float(seg.start),
            "end":   float(seg.end),
            "words": words,
        })

    return segments


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

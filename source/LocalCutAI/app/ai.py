from __future__ import annotations

from typing import Any, Callable


def transcribe_video(video_path: str, model_size: str = "base", progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Transcribe Polish speech locally on CPU (INT8); CUDA/NVIDIA is not used."""
    from faster_whisper import WhisperModel

    report = progress or (lambda _message: None)
    report(f"Ładowanie modelu Whisper „{model_size}” na procesorze CPU INT8 (pierwsze pobranie może potrwać)...")
    # Explicitly force CPU. This avoids requiring NVIDIA CUDA/cuBLAS/cuDNN DLLs.
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    report("Model działa lokalnie na CPU INT8. Karta NVIDIA nie jest używana.")

    report("Rozpoznawanie polskiej mowy i znaczników czasu słów...")
    segments_iter, info = model.transcribe(
        video_path,
        language="pl",
        task="transcribe",
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 350},
        condition_on_previous_text=True,
    )

    segments: list[dict[str, Any]] = []
    all_words: list[dict[str, Any]] = []
    for index, segment in enumerate(segments_iter, 1):
        item_words: list[dict[str, Any]] = []
        if segment.words:
            for word in segment.words:
                word_text = (word.word or "").strip()
                if not word_text:
                    continue
                w = {
                    "word": word_text,
                    "start": float(word.start if word.start is not None else segment.start),
                    "end": float(word.end if word.end is not None else segment.end),
                    "probability": float(word.probability if word.probability is not None else 1.0),
                }
                item_words.append(w)
                all_words.append(w)
        else:
            tokens = (segment.text or "").split()
            span = max(0.1, float(segment.end) - float(segment.start))
            step = span / max(1, len(tokens))
            for n, token in enumerate(tokens):
                w = {"word": token, "start": float(segment.start) + n * step, "end": float(segment.start) + (n + 1) * step, "probability": 1.0}
                item_words.append(w)
                all_words.append(w)
        segments.append({
            "start": float(segment.start),
            "end": float(segment.end),
            "text": (segment.text or "").strip(),
            "words": item_words,
        })
        if index == 1 or index % 12 == 0:
            report(f"Przetworzono {index} fragmentów mowy; zapisuję rozpoznany tekst...")

    if not segments:
        raise RuntimeError("Nie rozpoznano mowy. Sprawdź, czy film ma ścieżkę audio i czy słychać w nim głos.")
    return {
        "segments": segments,
        "words": sorted(all_words, key=lambda w: w["start"]),
        "device": "cpu",
        "language": getattr(info, "language", "pl"),
        "language_probability": float(getattr(info, "language_probability", 1.0) or 1.0),
    }

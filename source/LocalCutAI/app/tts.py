from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path
from typing import Any, Callable

from .video_ops import probe_duration, require_ffmpeg

Progress = Callable[[str], None]

# Polish Piper voices hosted by the public rhasspy/piper-voices repository.
# Voice files are downloaded on demand and kept locally in models/piper.
VOICE_CATALOG: dict[str, dict[str, str]] = {
    "pl_PL-gosia-medium": {
        "label": "Gosia — kobiecy, łagodny (medium)",
        "model": "pl/pl_PL/gosia/medium/pl_PL-gosia-medium.onnx",
    },
    "pl_PL-darkman-medium": {
        "label": "Darkman — męski, niski (medium)",
        "model": "pl/pl_PL/darkman/medium/pl_PL-darkman-medium.onnx",
    },
    "pl_PL-mc_speech-medium": {
        "label": "MC Speech — męski, wyraźny (medium)",
        "model": "pl/pl_PL/mc_speech/medium/pl_PL-mc_speech-medium.onnx",
    },
    "pl_PL-bass-high": {
        "label": "Bass — głęboki głos lektorski (high, ~114 MB)",
        "model": "pl/pl_PL/bass/high/pl_PL-bass-high.onnx",
    },
    "pl_PL-mls_6892-low": {
        "label": "MLS 6892 — dodatkowy głos (low)",
        "model": "pl/pl_PL/mls_6892/low/pl_PL-mls_6892-low.onnx",
    },
}

# Piper can adjust speaking rate and synthesis variation, but cannot truly add
# human emotions or clone a voice. These presets are subtle starting points;
# the best combination depends on the chosen voice and text.
SPEECH_STYLE_CATALOG: dict[str, dict[str, Any]] = {
    "natural": {
        "label": "Spokojny i naturalny (polecany)",
        "length_scale": 1.06,
        "noise_scale": 0.667,
        "noise_w_scale": 0.8,
        "help": "Trochę spokojniejsze tempo, z domyślną ekspresją modelu.",
    },
    "soft": {
        "label": "Miękki / stonowany",
        "length_scale": 1.10,
        "noise_scale": 0.60,
        "noise_w_scale": 0.72,
        "help": "Wolniejsze tempo i delikatniejsza zmienność syntezy.",
    },
    "neutral": {
        "label": "Neutralny (domyślne brzmienie modelu)",
        "length_scale": 1.0,
        "noise_scale": 0.667,
        "noise_w_scale": 0.8,
        "help": "Domyślne ustawienia danego głosu Piper.",
    },
    "dynamic": {
        "label": "Żywszy / dynamiczny",
        "length_scale": 0.94,
        "noise_scale": 0.72,
        "noise_w_scale": 0.88,
        "help": "Nieco szybsze tempo i większa zmienność syntezy.",
    },
}
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
SAMPLE_RATE = 22050


def _say(progress: Progress | None, message: str) -> None:
    if progress:
        progress(message)


def _project_root() -> Path:
    # In a PyInstaller build, keep downloaded voice models beside the executable,
    # not inside the temporary _MEIPASS extraction directory.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _download(url: str, destination: Path, progress: Progress | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "LocalCutAI/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response, temporary.open("wb") as out_file:
            total = int(response.headers.get("Content-Length", "0") or 0)
            done = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out_file.write(block)
                done += len(block)
                if total and progress:
                    progress(f"Pobieranie głosu: {destination.name} — {done * 100 // total}%")
        if not temporary.exists() or temporary.stat().st_size < 1000:
            raise RuntimeError(f"Pobrany plik głosu wygląda na niekompletny: {destination.name}")
        temporary.replace(destination)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def ensure_voice_files(voice_key: str, progress: Progress | None = None) -> tuple[Path, Path]:
    if voice_key not in VOICE_CATALOG:
        raise ValueError("Nieznany głos AI. Wybierz jeden z głosów z listy.")
    model_rel = VOICE_CATALOG[voice_key]["model"]
    voice_root = _project_root() / "models" / "piper"
    model_path = voice_root / Path(model_rel).name
    config_path = Path(str(model_path) + ".json")

    if not model_path.is_file() or model_path.stat().st_size < 1_000_000:
        size_hint = "około 110–115 MB" if voice_key == "pl_PL-bass-high" else "około 60–65 MB"
        _say(progress, f"Pobieram polski model głosu {VOICE_CATALOG[voice_key]['label']} ({size_hint}, tylko za pierwszym razem)...")
        _download(HF_BASE + model_rel + "?download=true", model_path, progress)
    config_url = HF_BASE + model_rel + ".json?download=true"
    if not config_path.is_file() or config_path.stat().st_size < 1000:
        _say(progress, f"Pobieram konfigurację głosu {VOICE_CATALOG[voice_key]['label']}...")
        _download(config_url, config_path, progress)

    return model_path, config_path


def _load_piper_voice(voice_key: str, progress: Progress | None = None):
    try:
        from piper import PiperVoice
    except ImportError as exc:
        raise RuntimeError(
            "Brak biblioteki Piper TTS. Zamknij LocalCut AI, uruchom install.bat w folderze projektu, "
            "a potem ponownie uruchom run.bat."
        ) from exc
    model_path, _config_path = ensure_voice_files(voice_key, progress)
    _say(progress, f"Ładowanie lokalnego głosu {VOICE_CATALOG[voice_key]['label']} na CPU...")
    return PiperVoice.load(str(model_path))


def _synthesis_config(style_key: str):
    """Build Piper settings for a speaking-style preset."""
    try:
        from piper import SynthesisConfig
    except ImportError as exc:
        raise RuntimeError(
            "Zainstalowana wersja Piper nie udostępnia SynthesisConfig. "
            "Uruchom install.bat, aby zaktualizować zależności."
        ) from exc
    style = SPEECH_STYLE_CATALOG.get(style_key, SPEECH_STYLE_CATALOG["natural"])
    return SynthesisConfig(
        length_scale=float(style["length_scale"]),
        noise_scale=float(style["noise_scale"]),
        noise_w_scale=float(style["noise_w_scale"]),
    )


def _synthesize_wav(voice, text: str, wav_file, style_key: str) -> None:
    """Synthesize a WAV using one of the selectable speech styles."""
    voice.synthesize_wav(text, wav_file, syn_config=_synthesis_config(style_key))


def generate_voice_preview(voice_key: str, output_path: str, text: str = "Cześć! To jest próbka głosu LocalCut AI.", progress: Progress | None = None, style_key: str = "natural") -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        text = "Cześć! To jest próbka głosu LocalCut AI."
    voice = _load_piper_voice(voice_key, progress)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _say(progress, "Generowanie krótkiej próbki głosu...")
    with wave.open(str(out), "wb") as wav_file:
        _synthesize_wav(voice, text[:1200], wav_file, style_key)
    return {
        "path": str(out),
        "voice": VOICE_CATALOG[voice_key]["label"],
        "style": SPEECH_STYLE_CATALOG.get(style_key, SPEECH_STYLE_CATALOG["natural"])["label"],
    }


def _probe_audio_duration(ffprobe: str, path: Path) -> float:
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Nie udało się odczytać czasu audio: {(proc.stderr or '')[-1000:]}")
    try:
        return float(json.loads(proc.stdout)["format"]["duration"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Nie udało się odczytać długości pliku audio: {path.name}") from exc


def _atempo_chain(speed: float) -> str:
    # FFmpeg atempo is commonly reliable within 0.5–2.0; chain filters for faster speech.
    factors: list[float] = []
    speed = max(1.0, float(speed))
    while speed > 2.0:
        factors.append(2.0)
        speed /= 2.0
    factors.append(speed)
    return ",".join(f"atempo={factor:.6f}" for factor in factors)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def render_voice_replacement(
    video_path: str,
    output_mp4: str,
    output_wav: str,
    rows: list[dict[str, Any]],
    voice_key: str,
    progress: Progress | None = None,
    style_key: str = "natural",
) -> dict[str, Any]:
    """Generate speech for edited transcript rows and replace the video's audio track.

    Speech starts at each row's start time. Its allowed slot ends at the row's end time,
    or the next row's start if that is earlier. Generated clips are only sped up when
    they would exceed their slot; silence remains between utterances.
    """
    ffmpeg, ffprobe = require_ffmpeg()
    source = Path(video_path).resolve()
    output = Path(output_mp4).resolve()
    wav_output = Path(output_wav).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Nie znaleziono filmu: {source}")
    duration = probe_duration(str(source))
    normalized: list[dict[str, Any]] = []
    for item in rows:
        text = _clean_text(item.get("text"))
        if not text:
            continue
        start = float(item.get("start", 0.0))
        end = float(item.get("end", 0.0))
        if start < 0 or end <= start:
            raise ValueError(f"Nieprawidłowy czas fragmentu: {start:.3f}–{end:.3f} s.")
        if start >= duration:
            continue
        normalized.append({"start": start, "end": min(end, duration), "text": text})
    normalized.sort(key=lambda item: (item["start"], item["end"]))
    if not normalized:
        raise ValueError("Nie ma żadnych niepustych fragmentów mowy do wygenerowania.")

    # Avoid two synthesized phrases fighting over the same part of the timeline.
    for idx, item in enumerate(normalized[:-1]):
        next_start = normalized[idx + 1]["start"]
        if next_start > item["start"]:
            item["end"] = min(item["end"], next_start)
        if item["end"] <= item["start"]:
            raise ValueError("Dwa fragmenty mają ten sam czas Start. Popraw czasy w tabeli lektora AI.")

    voice = _load_piper_voice(voice_key, progress)
    total_samples = max(1, int(round(duration * SAMPLE_RATE)))
    # One bytearray is sufficient: mono, signed 16-bit PCM at 22.05 kHz.
    timeline = bytearray(total_samples * 2)
    output.parent.mkdir(parents=True, exist_ok=True)
    wav_output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="localcut_tts_") as temp_name:
        temp = Path(temp_name)
        for index, item in enumerate(normalized, 1):
            start = float(item["start"])
            slot_duration = max(0.08, float(item["end"]) - start)
            safe_stem = f"part_{index:04d}"
            generated = temp / f"{safe_stem}_raw.wav"
            fitted = temp / f"{safe_stem}_fit.wav"
            _say(progress, f"Lektor AI: generowanie fragmentu {index}/{len(normalized)} ({start:.1f} s)...")
            with wave.open(str(generated), "wb") as wav_file:
                _synthesize_wav(voice, item["text"][:4000], wav_file, style_key)

            generated_duration = _probe_audio_duration(ffprobe, generated)
            filters: list[str] = []
            if generated_duration > slot_duration + 0.03:
                filters.append(_atempo_chain(generated_duration / slot_duration))
            filters.append(f"atrim=duration={slot_duration:.6f}")
            filters.append("asetpts=PTS-STARTPTS")
            cmd = [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(generated),
                "-af", ",".join(filters), "-ar", str(SAMPLE_RATE), "-ac", "1",
                "-c:a", "pcm_s16le", str(fitted),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if proc.returncode != 0:
                raise RuntimeError(f"Nie udało się dopasować fragmentu lektora nr {index}: {(proc.stderr or '')[-1200:]}")
            with wave.open(str(fitted), "rb") as wav_file:
                if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2 or wav_file.getframerate() != SAMPLE_RATE:
                    raise RuntimeError("Nieprawidłowy format roboczego audio lektora.")
                clip = wav_file.readframes(wav_file.getnframes())
            offset = max(0, int(round(start * SAMPLE_RATE))) * 2
            max_bytes = max(0, min(len(clip), len(timeline) - offset))
            # Rows are ordered and clipped at the next start, so this placement avoids overlap.
            if max_bytes:
                timeline[offset:offset + max_bytes] = clip[:max_bytes]

    _say(progress, "Zapisywanie pełnej ścieżki lektora AI...")
    with wave.open(str(wav_output), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(timeline)

    _say(progress, "Podmienianie oryginalnego audio i eksport MP4...")
    common = [
        ffmpeg, "-y", "-hide_banner", "-i", str(source), "-i", str(wav_output),
        "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{duration:.6f}", "-movflags", "+faststart",
    ]
    # Prefer a fast video stream copy; if the source codec/container combination is incompatible,
    # retry by transcoding video to broadly compatible H.264.
    proc = subprocess.run(common + ["-c:v", "copy", str(output)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        try:
            output.unlink(missing_ok=True)
        except OSError:
            pass
        proc = subprocess.run(common + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(output)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"Nie udało się zapisać MP4 z lektorem AI:\n{(proc.stderr or '')[-2400:]}")

    return {
        "path": str(output),
        "wav_path": str(wav_output),
        "voice": VOICE_CATALOG[voice_key]["label"],
        "style": SPEECH_STYLE_CATALOG.get(style_key, SPEECH_STYLE_CATALOG["natural"])["label"],
        "segments": len(normalized),
        "duration": round(duration, 2),
        "message": "Gotowe. Oryginalna ścieżka audio została zastąpiona lektorem AI; w przerwach między wypowiedziami jest cisza.",
    }

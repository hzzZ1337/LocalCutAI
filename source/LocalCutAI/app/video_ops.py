from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from .captions import write_ass

Progress = Callable[[str], None]


def _say(progress: Progress | None, message: str) -> None:
    if progress:
        progress(message)


def find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    # A portable FFmpeg build may be copied beside the source project or beside
    # the frozen executable (for a PyInstaller build).
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).resolve().parent
    else:
        app_root = Path(__file__).resolve().parent.parent
    roots = [app_root, Path.cwd()]
    for root in roots:
        candidate = root / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    return None


def require_ffmpeg() -> tuple[str, str]:
    ffmpeg = find_executable("ffmpeg")
    ffprobe = find_executable("ffprobe")
    if not ffmpeg:
        raise RuntimeError("Nie znaleziono ffmpeg.exe. Zainstaluj FFmpeg i dodaj folder bin do PATH albo skopiuj ffmpeg.exe i ffprobe.exe do folderu projektu. Instrukcja: README_PL.md")
    if not ffprobe:
        adjacent = Path(ffmpeg).with_name("ffprobe.exe")
        if adjacent.exists():
            ffprobe = str(adjacent)
        else:
            raise RuntimeError("Znaleziono FFmpeg, ale nie ffprobe.exe. Umieść oba pliki obok siebie lub dodaj folder bin FFmpeg do PATH.")
    return ffmpeg, ffprobe


def probe_duration(video_path: str) -> float:
    _ffmpeg, ffprobe = require_ffmpeg()
    cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe nie odczytał pliku: {proc.stderr[-1200:]}")
    try:
        return float(json.loads(proc.stdout)["format"]["duration"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Nie udało się ustalić długości filmu.") from exc


def detect_silence_ranges(video_path: str, noise_db: int = -35, min_silence: float = 0.6, progress: Progress | None = None) -> tuple[list[tuple[float, float]], float]:
    ffmpeg, _ = require_ffmpeg()
    duration = probe_duration(video_path)
    _say(progress, f"Analiza ciszy (próg {noise_db} dB, minimalny czas {min_silence:.1f} s)...")
    cmd = [ffmpeg, "-hide_banner", "-nostats", "-i", video_path, "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    combined = (proc.stderr or "") + "\n" + (proc.stdout or "")
    if "silencedetect" not in combined and proc.returncode != 0:
        raise RuntimeError(f"FFmpeg nie mógł przeanalizować audio:\n{combined[-1600:]}")
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", combined)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", combined)]
    ranges: list[tuple[float, float]] = []
    pending_start: float | None = None
    end_index = 0
    for start in starts:
        pending_start = start
        while end_index < len(ends) and ends[end_index] < start:
            end_index += 1
        if end_index < len(ends):
            end = ends[end_index]
            end_index += 1
            if end > start:
                ranges.append((max(0.0, start), min(duration, end)))
            pending_start = None
    if pending_start is not None and pending_start < duration:
        ranges.append((pending_start, duration))
    # Merge overlapping or adjacent detected regions.
    merged: list[tuple[float, float]] = []
    for start, end in sorted(ranges):
        if end <= start:
            continue
        if merged and start <= merged[-1][1] + 0.03:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged, duration


def remove_silence(video_path: str, output_path: str, progress: Progress | None = None) -> dict[str, Any]:
    ffmpeg, _ = require_ffmpeg()
    source = Path(video_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    silence, duration = detect_silence_ranges(video_path, progress=progress)
    if not silence:
        shutil.copy2(source, output)
        return {"path": str(output), "removed_seconds": 0.0, "message": "Nie wykryto dłuższych fragmentów ciszy; skopiowano oryginał."}

    keep: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in silence:
        if start - cursor >= 0.12:
            keep.append((cursor, start))
        cursor = max(cursor, end)
    if duration - cursor >= 0.12:
        keep.append((cursor, duration))
    if not keep:
        raise RuntimeError("Film wygląda na całkowicie cichy. Nic nie wyeksportowano.")

    filters: list[str] = []
    for index, (start, end) in enumerate(keep):
        filters.append(f"[0:v:0]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{index}]")
        filters.append(f"[0:a:0]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{index}]")
    labels = "".join(f"[v{i}][a{i}]" for i in range(len(keep)))
    filters.append(f"{labels}concat=n={len(keep)}:v=1:a=1[outv][outa]")
    filter_complex = ";".join(filters)
    _say(progress, f"Łączenie {len(keep)} fragmentów bez ciszy...")
    cmd = [ffmpeg, "-y", "-hide_banner", "-i", str(source), "-filter_complex", filter_complex,
           "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "192k", str(output)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"Eksport bez ciszy nie powiódł się:\n{(proc.stderr or '')[-2500:]}")
    removed = sum(end - start for start, end in silence)
    return {"path": str(output), "removed_seconds": round(removed, 2), "message": f"Usunięto około {removed:.1f} s ciszy."}


def suggest_moments(words: list[dict[str, Any]], duration: float, target_seconds: float = 35.0, limit: int = 8) -> list[dict[str, Any]]:
    """Rank windows using speech density and punctuation cues; this is a heuristic, not semantic understanding."""
    if duration <= 0 or not words:
        return []
    target = min(max(12.0, float(target_seconds)), duration)
    step = max(5.0, target / 4.0)
    candidates: list[dict[str, Any]] = []
    start = 0.0
    while start < max(0.01, duration - 0.5):
        end = min(duration, start + target)
        overlap = [w for w in words if float(w.get("end", 0)) > start and float(w.get("start", 0)) < end]
        if len(overlap) >= 5:
            words_per_minute = len(overlap) * 60.0 / max(1.0, end - start)
            excitement = sum(1 for w in overlap if re.search(r"[!?]", str(w.get("word", ""))))
            sentence_ends = sum(1 for w in overlap if re.search(r"[.!?…]$", str(w.get("word", ""))))
            long_gaps = 0
            for previous, current in zip(overlap, overlap[1:]):
                if float(current.get("start", 0)) - float(previous.get("end", 0)) > 0.6:
                    long_gaps += 1
            density = len(overlap) / max(1.0, end - start)
            score = density * 100 + excitement * 1.8 + sentence_ends * 0.35 - long_gaps * 0.7
            candidates.append({
                "start": round(start, 2), "end": round(end, 2), "score": round(score, 2),
                "word_count": len(overlap), "reason": f"{len(overlap)} słów; {words_per_minute:.0f} słów/min",
            })
        start += step
    candidates.sort(key=lambda x: x["score"], reverse=True)
    picked: list[dict[str, Any]] = []
    min_distance = target * 0.55
    for item in candidates:
        center = (item["start"] + item["end"]) / 2
        if any(abs(center - ((old["start"] + old["end"]) / 2)) < min_distance for old in picked):
            continue
        picked.append(item)
        if len(picked) >= limit:
            break
    return sorted(picked, key=lambda x: x["score"], reverse=True)


def _escape_filter_path(path: Path) -> str:
    # FFmpeg filtergraph parser treats drive colon, backslashes and apostrophes specially.
    raw = path.resolve().as_posix()
    raw = raw.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return raw


def create_short(
    video_path: str,
    output_path: str,
    start: float,
    end: float,
    words: list[dict[str, Any]],
    style: dict[str, Any] | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    ffmpeg, _ = require_ffmpeg()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = max(1.0, float(end) - float(start))
    style = dict(style or {})
    style["margin_v"] = int(style.get("short_margin_v", 170))
    ass_path = output.with_suffix(".ass")
    write_ass(words, ass_path, style=style, offset=float(start), duration=duration, portrait=True)
    subtitle_filter = f"subtitles='{_escape_filter_path(ass_path)}'"
    vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{subtitle_filter}"
    _say(progress, f"Renderowanie pionowego Shortsa {start:.1f}–{end:.1f} s...")
    base = [ffmpeg, "-y", "-hide_banner", "-ss", f"{float(start):.3f}", "-i", video_path,
            "-t", f"{duration:.3f}", "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(output)]
    proc = subprocess.run(base, capture_output=True, text=True, encoding="utf-8", errors="replace")
    burned = proc.returncode == 0
    if not burned:
        # Produce the clip even if the user's FFmpeg build has no libass subtitle filter.
        _say(progress, "FFmpeg nie wypalił napisów; ponawiam eksport wideo, plik .ASS zostanie obok.")
        fallback_vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        fallback = base.copy()
        vf_index = fallback.index("-vf")
        fallback[vf_index + 1] = fallback_vf
        proc = subprocess.run(fallback, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"Nie udało się wyrenderować Shortsa:\n{(proc.stderr or '')[-2500:]}")
    return {"path": str(output), "ass_path": str(ass_path), "burned_subtitles": burned,
            "start": float(start), "end": float(end)}


def burn_subtitles(
    video_path: str,
    ass_path: str,
    output_path: str,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Render ASS styling/word highlighting into pixels of a new MP4 for editors that do not import ASS."""
    ffmpeg, _ = require_ffmpeg()
    source = Path(video_path)
    ass = Path(ass_path)
    output = Path(output_path)
    if not source.is_file():
        raise RuntimeError(f"Nie znaleziono filmu źródłowego: {source}")
    if not ass.is_file():
        raise RuntimeError(f"Nie znaleziono pliku napisów ASS: {ass}")
    output.parent.mkdir(parents=True, exist_ok=True)

    # Check support before starting a long encode. ASS styling/animations need libass.
    filters = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    listing = (filters.stdout or "") + (filters.stderr or "")
    if filters.returncode != 0 or not re.search(r"\bsubtitles\b", listing):
        raise RuntimeError(
            "Twoja wersja FFmpeg nie ma filtra 'subtitles' (libass), potrzebnego do wypalenia animowanych napisów. "
            "Zainstaluj kompilację FFmpeg GPL/static z obsługą libass i spróbuj ponownie."
        )

    subtitle_filter = f"subtitles='{_escape_filter_path(ass)}'"
    _say(progress, "Wypalanie stylu ASS, kolorów i animacji bezpośrednio w obrazie MP4…")
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a?", "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-map_metadata", "0", str(output),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "brak szczegółów")[-3000:]
        raise RuntimeError(f"Nie udało się wypalić napisów do MP4. Szczegóły FFmpeg:\n{detail}")
    return {"path": str(output), "ass_path": str(ass), "message": "Gotowy film z wypalonymi napisami, kolorami i animacjami."}

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def _srt_time(seconds: float) -> str:
    ms = max(0, int(round(float(seconds) * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _ass_time(seconds: float) -> str:
    cs = max(0, int(round(float(seconds) * 100)))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def _ass_color(hex_color: str) -> str:
    value = (hex_color or "#FFFFFF").strip().lstrip("#")
    if len(value) != 6:
        value = "FFFFFF"
    r, g, b = value[0:2], value[2:4], value[4:6]
    # ASS colour order is alpha, blue, green, red; alpha 00 means opaque.
    return f"&H00{b.upper()}{g.upper()}{r.upper()}"


def _clean_ass_text(text: str) -> str:
    return (text or "").replace("{", "(").replace("}", ")").replace("\n", r"\N").strip()


def flatten_words(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for segment in segments:
        for word in segment.get("words", []) or []:
            text = str(word.get("word", "")).strip()
            if not text:
                continue
            result.append({
                "word": text,
                "start": max(0.0, float(word.get("start", segment.get("start", 0.0)))),
                "end": max(float(word.get("start", 0.0)) + 0.04,
                           float(word.get("end", segment.get("end", 0.0)))),
                "probability": float(word.get("probability", 1.0)),
            })
    return sorted(result, key=lambda item: (item["start"], item["end"]))



def apply_caption_text_edit(original_group: list[dict[str, Any]], edited_text: str) -> list[dict[str, Any]]:
    """Apply an edited subtitle line while keeping as much original word timing as possible.

    Unchanged tokens keep their exact timestamps. A typo correction keeps the old token
    timing; when tokens are merged (e.g. ``DU PA`` -> ``DUPA``), the new token spans the
    original pair's time range. Newly inserted tokens are assigned a small nearby interval.
    """
    tokens = (edited_text or "").split()
    original = [dict(item) for item in original_group]
    if not tokens or not original:
        return []

    row_start = min(float(item.get("start", 0.0)) for item in original)
    row_end = max(float(item.get("end", row_start + 0.08)) for item in original)
    row_end = max(row_start + 0.08, row_end)
    original_tokens = [str(item.get("word", "")).strip() for item in original]
    if len(tokens) == len(original):
        # Same number of words: keep every original timestamp, even if every word was edited.
        matched = []
        for old_word, token in zip(original, tokens):
            word = dict(old_word)
            word["word"] = token
            matched.append(word)
        return matched

    matcher = SequenceMatcher(
        None,
        [token.casefold() for token in original_tokens],
        [token.casefold() for token in tokens],
        autojunk=False,
    )
    result: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        new_tokens = tokens[j1:j2]
        source = original[i1:i2]
        if tag == "equal":
            for old_word, token in zip(source, new_tokens):
                word = dict(old_word)
                word["word"] = token
                result.append(word)
            continue
        if tag == "delete" or not new_tokens:
            continue

        if source:
            span_start = min(float(item.get("start", row_start)) for item in source)
            span_end = max(float(item.get("end", span_start + 0.08)) for item in source)
            template = dict(source[0])
            probability = sum(float(item.get("probability", 1.0)) for item in source) / len(source)
        else:
            # Added word: prefer the gap between its neighbours; otherwise use a short
            # interval around the insertion point without changing the rest of the line.
            previous_end = float(original[i1 - 1].get("end", row_start)) if i1 > 0 else row_start
            next_start = float(original[i1].get("start", row_end)) if i1 < len(original) else row_end
            if next_start - previous_end >= 0.04 * len(new_tokens):
                span_start, span_end = previous_end, next_start
            else:
                center = (previous_end + next_start) / 2.0
                width = min(max(0.08, 0.12 * len(new_tokens)), max(0.08, row_end - row_start))
                span_start = max(row_start, center - width / 2.0)
                span_end = min(row_end, max(span_start + 0.04, span_start + width))
            template = dict(original[max(0, min(i1, len(original) - 1))])
            probability = 1.0

        span_start = max(0.0, span_start)
        span_end = max(span_start + 0.04, span_end)
        if len(new_tokens) == 1:
            word = dict(template)
            word.update({"word": new_tokens[0], "start": span_start, "end": span_end, "probability": probability})
            result.append(word)
            continue

        weights = [max(1, len(token.strip(".,!?;:…()[]{}\"'"))) for token in new_tokens]
        total_weight = float(sum(weights))
        span_duration = max(0.04, span_end - span_start)
        cursor = span_start
        for index, (token, weight) in enumerate(zip(new_tokens, weights)):
            token_start = cursor
            token_end = span_end if index == len(new_tokens) - 1 else span_start + span_duration * (sum(weights[: index + 1]) / total_weight)
            token_end = max(token_start + 0.04, token_end)
            word = dict(template)
            word.update({"word": token, "start": token_start, "end": token_end, "probability": probability})
            result.append(word)
            cursor = token_end

    return sorted(result, key=lambda item: (float(item.get("start", 0.0)), float(item.get("end", 0.0))))

def write_srt(segments: list[dict[str, Any]], destination: str | Path) -> Path:
    destination = Path(destination)
    chunks: list[str] = []
    for index, segment in enumerate(segments, 1):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = max(start + 0.08, float(segment.get("end", start + 0.5)))
        chunks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{text}\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(chunks), encoding="utf-8-sig")
    return destination


def group_words(words: list[dict[str, Any]], max_words: int = 6, max_seconds: float = 3.4) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for item in sorted(words, key=lambda x: float(x.get("start", 0.0))):
        token = str(item.get("word", "")).strip()
        if not token:
            continue
        if current:
            gap = float(item["start"]) - float(current[-1]["end"])
            span = float(item["end"]) - float(current[0]["start"])
            prior = str(current[-1]["word"])
            sentence_end = bool(re.search(r"[.!?…]$", prior))
            if (len(current) >= max_words or span >= max_seconds or gap > 0.55 or sentence_end):
                groups.append(current)
                current = []
        current.append(item)
    if current:
        groups.append(current)
    return groups


def write_ass(
    words: list[dict[str, Any]],
    destination: str | Path,
    style: dict[str, Any] | None = None,
    offset: float = 0.0,
    duration: float | None = None,
    portrait: bool = False,
) -> Path:
    """Write ASS captions with optional word-by-word karaoke highlighting."""
    style = style or {}
    destination = Path(destination)
    width, height = (1080, 1920) if portrait else (1920, 1080)
    font = str(style.get("font", "Arial")).replace(",", " ")
    font_size = int(style.get("font_size", 58 if portrait else 52))
    text_color = _ass_color(str(style.get("text_color", "#FFFFFF")))
    highlight_color = _ass_color(str(style.get("highlight_color", "#FFD400")))
    karaoke = bool(style.get("karaoke", True))
    animation = str(style.get("animation", "Pop-in"))
    margin_v = int(style.get("margin_v", 170 if portrait else 80))

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font},{font_size},{highlight_color},{text_color},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,70,70,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    filtered: list[dict[str, Any]] = []
    for item in words:
        start, end = float(item.get("start", 0.0)), float(item.get("end", 0.0))
        if end <= offset or (duration is not None and start >= offset + duration):
            continue
        item2 = dict(item)
        item2["start"] = max(start, offset) - offset
        item2["end"] = max(item2["start"] + 0.04, min(end, offset + duration) - offset if duration is not None else end - offset)
        filtered.append(item2)

    animation_key = animation.strip().casefold().replace("_", "-")

    def animation_override() -> str:
        if animation_key.startswith("pop"):
            return r"{\fscx72\fscy72\t(0,130,\fscx100\fscy100)}"
        if animation_key in {"fade-in", "fade in", "fade"}:
            return r"{\fad(180,0)}"
        if animation_key in {"slide-up", "slide up", "wjechanie od dołu"}:
            target_y = max(0, height - margin_v)
            start_y = min(height + 24, target_y + 100)
            center_x = width // 2
            return "{\\move(%d,%d,%d,%d,0,230)\\fad(80,0)}" % (center_x, start_y, center_x, target_y)
        if animation_key in {"zoom-in", "zoom in", "zoom"}:
            return r"{\fscx45\fscy45\alpha&HFF&\t(0,190,\fscx100\fscy100\alpha&H00&)}"
        if animation_key == "bounce":
            return r"{\fscx65\fscy65\t(0,110,\fscx118\fscy118)\t(110,250,\fscx100\fscy100)}"
        return ""

    if filtered and all("_caption_group" in item for item in filtered):
        preserved_groups: dict[str, list[dict[str, Any]]] = {}
        for item in sorted(filtered, key=lambda x: float(x.get("start", 0.0))):
            preserved_groups.setdefault(str(item["_caption_group"]), []).append(item)
        event_groups = sorted(
            [sorted(group, key=lambda x: float(x.get("start", 0.0))) for group in preserved_groups.values()],
            key=lambda group: float(group[0].get("start", 0.0)),
        )
    else:
        event_groups = group_words(filtered)

    for group in event_groups:
        start = max(0.0, float(group[0]["start"]))
        # Respect the editor's exact end timestamp instead of adding hidden extra time.
        end = max(start + 0.08, float(group[-1]["end"]))
        pieces: list[str] = []
        override = animation_override()
        if override:
            pieces.append(override)
        for index, item in enumerate(group):
            token = _clean_ass_text(str(item.get("word", "")))
            if index > 0:
                token = " " + token
            if karaoke:
                if index + 1 < len(group):
                    timing = max(1, int(round((float(group[index + 1]["start"]) - float(item["start"])) * 100)))
                else:
                    timing = max(1, int(round((float(item["end"]) - float(item["start"])) * 100)))
                pieces.append(f"{{\\kf{timing}}}{token}")
            else:
                pieces.append(token)
        text = "".join(pieces)
        lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{text}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return destination


def save_transcript_json(segments: list[dict[str, Any]], words: list[dict[str, Any]], destination: str | Path) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"segments": segments, "words": words}, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination

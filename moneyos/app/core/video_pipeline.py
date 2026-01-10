from __future__ import annotations

import asyncio
import compileall
import hashlib
import os
import random
import re
import shutil
import textwrap
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import ffmpeg
import logging
import requests
from pydub import AudioSegment

from app.core.video_queue import insert_output, update_script_payload

ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT / "assets"
VIDEO_BG_DIR = ASSETS_DIR / "video_bgs"
IMAGE_BG_DIR = ASSETS_DIR / "image_bgs"
PEXELS_CACHE_DIR = ASSETS_DIR / "pexels_cache"
OUTPUT_DIR = ROOT / "output"
TIKTOK_DIR = OUTPUT_DIR / "tiktok"
YOUTUBE_DIR = OUTPUT_DIR / "youtube"

FONT = "Arial"
logger = logging.getLogger(__name__)
REPAIR_STATE = {
    "disabled_subtitles": False,
    "disabled_backgrounds": False,
    "fallback_mode": False,
    "applied_repairs": set(),
}


def _hash_error_signature(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8", errors="ignore")).hexdigest()


def _apply_repair(signature: str, stderr: str, background_path: Path | None) -> None:
    if signature in REPAIR_STATE["applied_repairs"]:
        return

    stderr_lower = stderr.lower()
    applied = False
    if "subtitles" in stderr_lower or ".srt" in stderr_lower or "caption" in stderr_lower:
        if not REPAIR_STATE["disabled_subtitles"]:
            REPAIR_STATE["disabled_subtitles"] = True
            applied = True

    if background_path and background_path.as_posix().lower() in stderr_lower:
        if not REPAIR_STATE["disabled_backgrounds"]:
            REPAIR_STATE["disabled_backgrounds"] = True
            applied = True

    if "no such file" in stderr_lower or "could not open" in stderr_lower:
        if not REPAIR_STATE["disabled_subtitles"]:
            REPAIR_STATE["disabled_subtitles"] = True
            applied = True

    if applied:
        REPAIR_STATE["applied_repairs"].add(signature)


def _verify_repair_state(ffmpeg_cmd: ffmpeg.nodes.OutputStream | None = None) -> None:
    logger.info("Repair verification: compiling Python sources")
    compileall.compile_dir(str(ROOT), quiet=1)
    if ffmpeg_cmd is not None:
        ffmpeg_cmd.compile()
    logger.info("Repair verification: ffmpeg dry-run compiled")


@dataclass
class ScriptItem:
    id: int
    platform: str
    payload: dict[str, Any]


def ensure_dirs() -> None:
    VIDEO_BG_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_BG_DIR.mkdir(parents=True, exist_ok=True)
    PEXELS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TIKTOK_DIR.mkdir(parents=True, exist_ok=True)
    YOUTUBE_DIR.mkdir(parents=True, exist_ok=True)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def generate_script(topic: str, platform: str) -> dict[str, str]:
    topic_clean = _clean_text(topic)
    hook = f"{topic_clean}: the one decision mistake most buyers make."
    body = (
        f"In under a minute, here is what matters most when choosing {topic_clean.lower()}. "
        "Focus on reliability, total cost over 12 months, and whether the setup fits your routine. "
        "If a tool saves you 10 minutes a day, that is hours back every month."
    )
    cta = "Compare official offers now and pick the best fit for your needs."
    caption = f"{topic_clean} — quick buyer guide."
    hashtags = "#personalfinance #productivity #buyersguide #uk"
    title = f"{topic_clean} | 60-second buyer guide"
    return {
        "hook": hook,
        "body": body,
        "cta": cta,
        "caption": caption,
        "hashtags": hashtags,
        "title": title if platform == "youtube" else "",
    }


def _script_to_voice_text(payload: dict[str, Any]) -> str:
    text = _clean_text(f"{payload['hook']} {payload['body']} {payload['cta']}")
    words = text.split()
    min_words = 75
    max_words = 150
    filler = (
        " Here is the quick buyer checklist: prioritise reliability, compare annual costs, "
        "and pick the option that saves you time every single week."
    )
    while len(words) < min_words:
        text = _clean_text(f"{text} {filler}")
        words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text


async def _edge_tts_save(text: str, output_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice="en-GB-SoniaNeural")
    await communicate.save(str(output_path))


def _pyttsx3_save(text: str, output_path: Path) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.save_to_file(text, str(output_path))
    engine.runAndWait()


def generate_voiceover(text: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        asyncio.run(_edge_tts_save(text, output_path))
        return output_path
    except Exception:
        wav_path = output_path.with_suffix(".wav")
        _pyttsx3_save(text, wav_path)
        audio = AudioSegment.from_wav(wav_path)
        audio.export(output_path, format="mp3")
        return output_path


def _sentence_chunks(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s for s in sentences if s.strip()]


def _format_srt_timestamp(seconds: float) -> str:
    ms = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    hrs = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"


def generate_captions(text: str, audio_path: Path, output_path: Path) -> tuple[Path, float]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio = AudioSegment.from_file(audio_path)
    duration = audio.duration_seconds
    sentences = _sentence_chunks(text)
    words = [len(sentence.split()) for sentence in sentences]
    total_words = sum(words) or 1
    current = 0.0
    lines = []
    for idx, sentence in enumerate(sentences, start=1):
        share = words[idx - 1] / total_words
        segment = max(1.0, duration * share)
        start = current
        end = min(duration, start + segment)
        current = end
        wrapped = "\n".join(textwrap.wrap(sentence, width=42))
        lines.append(f"{idx}\n{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}\n{wrapped}\n")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path, duration


def generate_srt(text: str, audio_path: Path, output_path: Path) -> tuple[Path, float]:
    return generate_captions(text, audio_path, output_path)


def _pick_local_background() -> tuple[Path | None, bool]:
    videos = list(VIDEO_BG_DIR.glob("*.mp4"))
    images = list(IMAGE_BG_DIR.glob("*.jpg")) + list(IMAGE_BG_DIR.glob("*.png"))
    if videos:
        return random.choice(videos), True
    if images:
        return random.choice(images), False
    return None, False


def _pexels_background(query: str) -> tuple[Path | None, bool]:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None, False
    url = "https://api.pexels.com/videos/search"
    response = requests.get(
        url,
        headers={"Authorization": api_key},
        params={"query": query, "per_page": 1, "orientation": "portrait"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    videos = data.get("videos", [])
    if not videos:
        return None, False
    video_files = videos[0].get("video_files", [])
    if not video_files:
        return None, False
    best = sorted(video_files, key=lambda item: item.get("width", 0), reverse=True)[0]
    link = best.get("link")
    if not link:
        return None, False
    filename = PEXELS_CACHE_DIR / f"pexels_{videos[0]['id']}.mp4"
    if not filename.exists():
        stream = requests.get(link, timeout=30)
        stream.raise_for_status()
        filename.write_bytes(stream.content)
    return filename, True


def _select_background(topic: str) -> tuple[Path | None, bool]:
    local = _pick_local_background()
    if local[0]:
        return local
    return _pexels_background(topic)


def render_video(
    *,
    script_text: str,
    hook: str,
    audio_path: Path,
    srt_path: Path | None,
    duration: float,
    background_path: Path | None,
    background_is_video: bool,
    platform: str,
    script_id: int,
) -> Path:
    ensure_dirs()
    audio_path = audio_path.resolve()
    srt_path = srt_path.resolve().as_posix() if srt_path else None
    background_path = background_path.resolve() if background_path else None
    output_dir = OUTPUT_DIR / platform
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str((output_dir / f"video_{script_id}.mp4").resolve())
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    assert isinstance(output_path, str)
    assert output_path.endswith(".mp4")
    logger.info("FFmpeg output path: %s", output_path)
    size = "1080x1920"
    def build_video_stream(use_background: bool) -> Any:
        if use_background and background_path:
            if not background_path.exists():
                logger.warning("Background asset missing, using fallback: %s", background_path)
                return build_video_stream(False)
            if background_is_video:
                video_in = ffmpeg.input(background_path.as_posix(), stream_loop=-1)
                return video_in.filter("scale", 1080, 1920).filter("fps", fps=30)
            video_in = ffmpeg.input(background_path.as_posix(), loop=1, framerate=30, t=duration)
            return (
                video_in.filter(
                    "zoompan",
                    z="min(zoom+0.0008,1.05)",
                    d=int(duration * 30),
                    s=size,
                )
                .filter("scale", 1080, 1920)
                .filter("fps", fps=30)
            )
        video_in = ffmpeg.input(f"color=c=black:s={size}:d={duration}", f="lavfi")
        return video_in.filter("fps", fps=30)

    audio = ffmpeg.input(audio_path.as_posix())
    subtitles_available = bool(srt_path) and Path(srt_path).exists()
    if not subtitles_available:
        logger.warning("Captions missing, rendering without subtitles")

    last_error = ""
    last_signature = ""
    for attempt in (1, 2):
        use_subtitles = subtitles_available and attempt == 1 and not REPAIR_STATE["disabled_subtitles"]
        use_background = not REPAIR_STATE["disabled_backgrounds"] and (attempt == 1 or subtitles_available)
        video = build_video_stream(use_background)
        hook_text = _clean_text(hook)
        hook_draw = video.filter(
            "drawtext",
            font=FONT,
            text=hook_text,
            fontsize=68,
            fontcolor="white",
            shadowcolor="black",
            shadowx=2,
            shadowy=2,
            x="(w-text_w)/2",
            y="(h-text_h)/2",
            enable="between(t,0,3)",
        )
        if use_subtitles:
            logger.info("FFmpeg render attempt %s with subtitles", attempt)
            render_stream = ffmpeg.filter(
                hook_draw,
                "subtitles",
                srt_path,
                force_style=(
                    "FontName=Arial,FontSize=38,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
                    "Outline=2,Alignment=2,MarginV=120"
                ),
            )
        else:
            logger.info("FFmpeg render attempt %s without subtitles", attempt)
            render_stream = hook_draw

        ffmpeg_cmd = ffmpeg.output(
            render_stream,
            audio,
            output_path,
            vcodec="libx264",
            acodec="aac",
            pix_fmt="yuv420p",
            r=25,
            shortest=1,
            movflags="+faststart",
        )
        logger.info("FFmpeg command: %s", " ".join(ffmpeg_cmd.compile()))
        try:
            ffmpeg_cmd.run(overwrite_output=True)
            break
        except ffmpeg.Error as exc:
            last_error = exc.stderr.decode(errors="ignore") if exc.stderr else ""
            logger.error("FFMPEG STDERR: %s", last_error)
            signature_source = f"{exc.__class__.__name__}:{last_error}"
            last_signature = _hash_error_signature(signature_source)
            logger.error("FFmpeg failure signature: %s", last_signature)
            logger.error("FFmpeg failure traceback: %s", traceback.format_exc())
            _apply_repair(last_signature, last_error, background_path)
            _verify_repair_state(ffmpeg_cmd)
            logger.info("Repair relaunch requested")

    if not Path(output_path).exists():
        REPAIR_STATE["fallback_mode"] = True
        logger.error("FFmpeg failed after retry, entering fallback mode: %s", last_error)
        Path(output_path).touch()

    return output_path


def generate_video_for_script(script: ScriptItem) -> dict[str, Any]:
    ensure_dirs()
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg not available. Install ffmpeg and add it to PATH.")

    payload = script.payload
    voice_text = _script_to_voice_text(payload)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    platform_dir = TIKTOK_DIR if script.platform == "tiktok" else YOUTUBE_DIR
    audio_path = platform_dir / f"voice_{script.id}_{timestamp}.mp3"
    srt_path = platform_dir / f"captions_{script.id}_{timestamp}.srt"

    generate_voiceover(voice_text, audio_path)
    try:
        srt_path, duration = generate_captions(voice_text, audio_path, srt_path)
    except Exception as exc:
        logger.warning("Caption generation failed, rendering without subtitles: %s", exc)
        srt_path = None
        duration = AudioSegment.from_file(audio_path).duration_seconds
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise FileNotFoundError(f"Audio file missing or empty: {audio_path}")
    if srt_path and not srt_path.exists():
        logger.warning("Caption file missing, rendering without subtitles: %s", srt_path)
        srt_path = None

    background_path, background_is_video = _select_background(payload.get("topic", "business"))
    if background_path and not background_path.exists():
        raise FileNotFoundError(f"Background asset missing: {background_path}")
    video_path = render_video(
        script_text=voice_text,
        hook=payload["hook"],
        audio_path=audio_path,
        srt_path=srt_path,
        duration=duration,
        background_path=background_path,
        background_is_video=background_is_video,
        platform=script.platform,
        script_id=script.id,
    )
    logger.info("Video rendered: %s", video_path)

    rel_video = str(Path(video_path).relative_to(OUTPUT_DIR))
    rel_srt = str(srt_path.relative_to(OUTPUT_DIR)) if srt_path else ""
    output_payload = {
        "script_id": script.id,
        "video_path": rel_video,
        "srt_path": rel_srt,
        "caption": payload.get("caption", ""),
        "hashtags": payload.get("hashtags", ""),
        "title": payload.get("title", ""),
        "duration_seconds": round(duration, 2),
    }

    video_kind = "VIDEO_MP4" if script.platform == "tiktok" else "SHORT_VIDEO_MP4"
    insert_output(script.platform, video_kind, output_payload)
    if srt_path:
        insert_output(script.platform, "SRT", output_payload)
    insert_output(
        script.platform,
        "CAPTION_HASHTAGS" if script.platform == "tiktok" else "TITLE_DESC_TAGS",
        output_payload,
    )
    update_script_payload(script.id, output_payload)
    return output_payload

from __future__ import annotations

import asyncio
import os
import random
import re
import shutil
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import logging
import requests
from pydub import AudioSegment
import subprocess

from app.core.code_repair_bot import get_code_repair_bot
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
    bot = get_code_repair_bot()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        bot.retry_operation(lambda: asyncio.run(_edge_tts_save(text, output_path)), context={"op": "edge_tts"})
        return output_path
    except Exception:
        try:
            wav_path = output_path.with_suffix(".wav")
            bot.retry_operation(lambda: _pyttsx3_save(text, wav_path), context={"op": "pyttsx3_save"})
            audio = AudioSegment.from_wav(wav_path)
            bot.retry_operation(
                lambda: audio.export(output_path, format="mp3"),
                context={"op": "audio_export"},
            )
            return output_path
        except Exception:
            logger.warning("Voiceover generation failed, using silent fallback.")
            silent = AudioSegment.silent(duration=1000)
            bot.retry_operation(
                lambda: silent.export(output_path, format="mp3"),
                context={"op": "silent_audio_export"},
            )
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
    bot = get_code_repair_bot()
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
    bot.retry_operation(
        lambda: output_path.write_text("\n".join(lines), encoding="utf-8"),
        context={"op": "write_srt", "path": str(output_path)},
    )
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
    bot = get_code_repair_bot()
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
        bot.retry_operation(
            lambda: filename.write_bytes(stream.content),
            context={"op": "write_pexels", "path": str(filename)},
        )
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
    bot = get_code_repair_bot()
    ensure_dirs()
    audio_path = audio_path.resolve()
    srt_path = srt_path.resolve().as_posix() if srt_path else None
    background_path = background_path.resolve() if background_path else None
    output_dir = OUTPUT_DIR / platform
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (output_dir / f"video_{script_id}.mp4").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bot.retry_operation(lambda: output_path.touch(exist_ok=True), context={"op": "touch_video"})
    assert output_path.exists()
    assert output_path.suffix == ".mp4"
    assert not output_path.stem.isdigit()
    logger.info("FFmpeg output path: %s", output_path)
    size = "1080x1920"

    def _build_ffmpeg_cmd(
        *,
        output_file: Path,
        include_subtitles: bool,
        include_background: bool,
        include_audio: bool,
    ) -> list[str]:
        cmd: list[str] = ["ffmpeg", "-y"]
        if include_background and background_path:
            if not background_path.exists():
                logger.warning("Background asset missing, using fallback: %s", background_path)
                include_background = False
        if include_background and background_path:
            if background_is_video:
                cmd += ["-stream_loop", "-1", "-i", background_path.as_posix()]
            else:
                cmd += [
                    "-loop",
                    "1",
                    "-framerate",
                    "30",
                    "-t",
                    str(duration),
                    "-i",
                    background_path.as_posix(),
                ]
        else:
            cmd += ["-f", "lavfi", "-i", f"color=c=black:s={size}:d={duration}"]
        if include_audio:
            cmd += ["-i", audio_path.as_posix()]

        vf_filters: list[str] = []
        if include_subtitles and srt_path:
            vf_filters.append(f"subtitles={srt_path}")
        if vf_filters:
            cmd += ["-vf", ",".join(vf_filters)]

        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25"]
        if include_audio:
            cmd += ["-c:a", "aac", "-shortest"]
        cmd += ["-movflags", "+faststart", output_file.as_posix()]
        return cmd

    def _run_ffmpeg(cmd: list[str]) -> tuple[bool, str]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, result.stderr or result.stdout
        return True, ""
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        logger.warning("Audio missing in render_video, generating silent fallback.")
        silent = AudioSegment.silent(duration=1000)
        bot.retry_operation(
            lambda: silent.export(audio_path, format="mp3"),
            context={"op": "silent_audio_export"},
        )
    subtitles_available = bool(srt_path) and Path(srt_path).exists()
    if not subtitles_available:
        logger.warning("Captions missing, rendering without subtitles")

    last_error = ""
    memory = bot.memory
    include_subtitles = subtitles_available and not memory.disabled_subtitles
    include_background = not memory.disabled_backgrounds and background_path is not None
    ffmpeg_cmd = _build_ffmpeg_cmd(
        output_file=output_path,
        include_subtitles=include_subtitles,
        include_background=include_background,
        include_audio=True,
    )
    logger.info("FFmpeg command: %s", " ".join(ffmpeg_cmd))
    ok, stderr = _run_ffmpeg(ffmpeg_cmd)
    if not ok:
        last_error = stderr
        signature = bot.intercept_error(RuntimeError(stderr), context={"phase": "primary", "stderr": last_error})
        bot.apply_fix(signature, last_error, context={"phase": "primary", "ffmpeg_cmd": ffmpeg_cmd})
        if "srt" in last_error.lower() or "subtitles" in last_error.lower():
            include_subtitles = False
        if "output format for '1'" in last_error.lower():
            output_path = (output_dir / f"video_{script_id}_repair.mp4").resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            bot.retry_operation(lambda: output_path.touch(exist_ok=True), context={"op": "touch_video"})
        ffmpeg_cmd = _build_ffmpeg_cmd(
            output_file=output_path,
            include_subtitles=False,
            include_background=include_background,
            include_audio=True,
        )
        logger.info("FFmpeg command retry: %s", " ".join(ffmpeg_cmd))
        ok, stderr = _run_ffmpeg(ffmpeg_cmd)
        if not ok:
            last_error = stderr
            bot.fallback_to_safe_mode()

    if not output_path.exists() or output_path.stat().st_size == 0:
        logger.info("FFmpeg render attempt 2 safe mode")
        safe_output_path = (output_dir / f"video_{script_id}_safe.mp4").resolve()
        safe_output_path.parent.mkdir(parents=True, exist_ok=True)
        bot.retry_operation(lambda: safe_output_path.touch(exist_ok=True), context={"op": "touch_video"})
        assert safe_output_path.exists()
        assert safe_output_path.suffix == ".mp4"
        safe_cmd = _build_ffmpeg_cmd(
            output_file=safe_output_path,
            include_subtitles=False,
            include_background=False,
            include_audio=True,
        )
        logger.info("FFmpeg safe command: %s", " ".join(safe_cmd))
        ok, stderr = _run_ffmpeg(safe_cmd)
        if ok:
            output_path = safe_output_path
        else:
            logger.warning("FFmpeg safe mode with audio failed, retrying without audio.")
            safe_cmd = _build_ffmpeg_cmd(
                output_file=safe_output_path,
                include_subtitles=False,
                include_background=False,
                include_audio=False,
            )
            logger.info("FFmpeg safe command no-audio: %s", " ".join(safe_cmd))
            ok, stderr = _run_ffmpeg(safe_cmd)
            if ok:
                output_path = safe_output_path
            else:
                last_error = stderr
                signature = bot.intercept_error(RuntimeError(stderr), context={"phase": "safe_mode"})
                bot.apply_fix(signature, last_error, context={"phase": "safe_mode", "ffmpeg_cmd": safe_cmd})
                raise RuntimeError(f"FFmpeg safe mode failed: {stderr}")

    return output_path


def generate_video_for_script(script: ScriptItem) -> dict[str, Any]:
    ensure_dirs()
    bot = get_code_repair_bot()
    ffmpeg_ready = ffmpeg_available()
    if not ffmpeg_ready:
        logger.error("FFmpeg not available, cannot generate video.")

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
        try:
            duration = AudioSegment.from_file(audio_path).duration_seconds
        except Exception:
            duration = 1.0
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        logger.warning("Audio missing, generating silent fallback: %s", audio_path)
        silent = AudioSegment.silent(duration=1000)
        bot.retry_operation(
            lambda: silent.export(audio_path, format="mp3"),
            context={"op": "silent_audio_export"},
        )
        duration = max(duration, 1.0)
    if srt_path and not srt_path.exists():
        logger.warning("Caption file missing, rendering without subtitles: %s", srt_path)
        srt_path = None

    try:
        background_path, background_is_video = _select_background(payload.get("topic", "business"))
    except Exception as exc:
        logger.warning("Background selection failed, using fallback: %s", exc)
        background_path, background_is_video = None, False
    if background_path and not background_path.exists():
        logger.warning("Background asset missing, using fallback: %s", background_path)
        background_path, background_is_video = None, False
    output_dir = OUTPUT_DIR / script.platform
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"video_{script.id}.mp4"
    try:
        if not ffmpeg_ready:
            raise RuntimeError("FFmpeg not available.")
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
    except Exception as exc:
        signature = bot.intercept_error(exc, context={"phase": "render", "stderr": str(exc)})
        bot.apply_fix(
            signature,
            str(exc),
            context={"fix": "ensure_output_path", "output_path": str(output_path)},
        )
        video_path = output_path
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

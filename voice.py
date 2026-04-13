#!/usr/bin/env python3
"""
tts_cache_test.py

Offline cross-platform TTS test helper for Windows + Linux using pyttsx3.

What it does:
- Accepts input text from the command line
- Saves generated speech into ./tts_cache/
- Reuses cached WAV files for repeated phrases
- Plays WAV files on:
    - Windows: winsound
    - Linux: aplay
- Prints generation/playback timings
- Lets you pick a default voice in this file
- Lets you override the voice from the command line

Install:
    pip install pyttsx3

Linux notes:
- You will likely need:
    sudo apt install espeak-ng alsa-utils
- 'aplay' comes from alsa-utils
"""

from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pyttsx3


# ============================================================
# DEFAULT SETTINGS YOU CAN EDIT HERE
# ============================================================

CACHE_DIR = Path("tts_cache")

DEFAULT_TEXT = "Path divergence detected. Take the right door."

# Default speech settings
DEFAULT_RATE = 175
DEFAULT_VOLUME = 1.0

# Choose ONE of these methods:

# Method 1: Set a default voice index after testing with --list-voices
# Example: 0, 1, 2, etc.
DEFAULT_VOICE_INDEX = None

# Method 2: Set a keyword to search for in the voice id/name
# This is often better across machines than a fixed index.
# Examples:
#   Windows: "zira", "david"
#   Linux:   "english", "english-us", "en"
DEFAULT_VOICE_KEYWORD = None

# If both are None, the system default voice is used.


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_name(text: str, max_len: int = 40) -> str:
    """
    Build a short stable filename from input text.
    Prevents huge ugly filenames.
    """
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in text)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    cleaned = cleaned[:max_len].rstrip("_")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{cleaned or 'voice'}_{digest}"


def ensure_cache_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def list_voices(engine: pyttsx3.Engine) -> None:
    voices = engine.getProperty("voices")
    print("\nAvailable voices:\n")
    for i, voice in enumerate(voices):
        name = getattr(voice, "name", "unknown")
        vid = getattr(voice, "id", "unknown")
        langs = getattr(voice, "languages", None)
        gender = getattr(voice, "gender", None)
        age = getattr(voice, "age", None)

        print(f"[{i}]")
        print(f"  name     : {name}")
        print(f"  id       : {vid}")
        print(f"  languages: {langs}")
        print(f"  gender   : {gender}")
        print(f"  age      : {age}")
        print()


def choose_voice(
    engine: pyttsx3.Engine,
    voice_index: int | None = None,
    voice_keyword: str | None = None,
) -> str | None:
    """
    Pick a voice by index or keyword.
    Returns the selected voice id, or None if default voice is used.
    """
    voices = engine.getProperty("voices")

    if not voices:
        return None

    if voice_index is not None:
        if voice_index < 0 or voice_index >= len(voices):
            raise ValueError(
                f"Invalid voice index {voice_index}. "
                f"Available voices: 0 to {len(voices) - 1}"
            )
        voice_id = voices[voice_index].id
        engine.setProperty("voice", voice_id)
        return voice_id

    if voice_keyword:
        keyword = voice_keyword.lower()
        for voice in voices:
            voice_id = str(getattr(voice, "id", "")).lower()
            voice_name = str(getattr(voice, "name", "")).lower()

            if keyword in voice_id or keyword in voice_name:
                engine.setProperty("voice", voice.id)
                return voice.id

    return None


def wait_for_file(file_path: Path, timeout: float = 10.0) -> None:
    """
    Wait until the file exists and has non-zero size.
    """
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if file_path.exists() and file_path.stat().st_size > 0:
            return
        time.sleep(0.05)

    raise TimeoutError(f"Timed out waiting for output file: {file_path}")


def generate_tts_file(
    text: str,
    output_path: Path,
    rate: int,
    volume: float,
    voice_index: int | None,
    voice_keyword: str | None,
) -> tuple[float, str | None]:
    """
    Generate a WAV file with pyttsx3.
    Returns:
        (generation_time_seconds, selected_voice_id)
    """
    start = time.perf_counter()

    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)

    selected_voice = choose_voice(
        engine,
        voice_index=voice_index,
        voice_keyword=voice_keyword,
    )

    if output_path.exists():
        output_path.unlink()

    engine.save_to_file(text, str(output_path))
    engine.runAndWait()
    engine.stop()

    wait_for_file(output_path)

    elapsed = time.perf_counter() - start
    return elapsed, selected_voice


def play_audio(file_path: Path) -> float:
    """
    Play a WAV file on Windows or Linux.
    Windows -> winsound
    Linux   -> aplay
    """
    system = platform.system().lower()
    start = time.perf_counter()

    if "windows" in system:
        import winsound
        winsound.PlaySound(str(file_path), winsound.SND_FILENAME)

    elif "linux" in system:
        if shutil.which("aplay") is None:
            raise RuntimeError(
                "Linux playback requires 'aplay'. Install it with your package manager."
            )

        result = subprocess.run(
            ["aplay", str(file_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"aplay failed:\n{result.stderr.strip()}")

    else:
        raise RuntimeError(
            f"Unsupported OS: {platform.system()}. This script is for Windows and Linux."
        )

    elapsed = time.perf_counter() - start
    return elapsed


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline TTS cache test for Windows + Linux using pyttsx3"
    )

    parser.add_argument(
        "text",
        nargs="?",
        default=DEFAULT_TEXT,
        help="Text to convert to speech",
    )

    parser.add_argument(
        "--rate",
        type=int,
        default=DEFAULT_RATE,
        help=f"Speech rate (default: {DEFAULT_RATE})",
    )

    parser.add_argument(
        "--volume",
        type=float,
        default=DEFAULT_VOLUME,
        help=f"Volume from 0.0 to 1.0 (default: {DEFAULT_VOLUME})",
    )

    parser.add_argument(
        "--voice",
        type=int,
        default=None,
        help="Override voice by index from --list-voices",
    )

    parser.add_argument(
        "--voice-keyword",
        type=str,
        default=None,
        help="Override voice by keyword match against voice id/name",
    )

    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate the file even if it already exists in cache",
    )

    parser.add_argument(
        "--no-play",
        action="store_true",
        help="Generate only, do not play the WAV",
    )

    args = parser.parse_args()

    ensure_cache_dir(CACHE_DIR)

    engine = pyttsx3.init()

    if args.list_voices:
        list_voices(engine)
        engine.stop()
        return

    engine.stop()

    text = args.text.strip()
    if not text:
        raise ValueError("Input text is empty.")

    # Command line overrides file defaults
    selected_voice_index = args.voice if args.voice is not None else DEFAULT_VOICE_INDEX
    selected_voice_keyword = (
        args.voice_keyword
        if args.voice_keyword is not None
        else DEFAULT_VOICE_KEYWORD
    )

    base_name = safe_name(text)
    out_file = CACHE_DIR / f"{base_name}.wav"

    print(f"Input text     : {text}")
    print(f"Output file    : {out_file}")
    print(f"Rate           : {args.rate}")
    print(f"Volume         : {args.volume}")
    print(f"Voice index    : {selected_voice_index}")
    print(f"Voice keyword  : {selected_voice_keyword}")
    print()

    generated = False
    generation_time = 0.0
    selected_voice_id = None

    if out_file.exists() and not args.force:
        print("Cache hit: using existing WAV.")
    else:
        print("Generating speech...")
        generation_time, selected_voice_id = generate_tts_file(
            text=text,
            output_path=out_file,
            rate=args.rate,
            volume=args.volume,
            voice_index=selected_voice_index,
            voice_keyword=selected_voice_keyword,
        )
        generated = True

    print(f"File exists     : {out_file.exists()}")
    print(f"File size       : {out_file.stat().st_size} bytes")

    if generated:
        print(f"Generation time : {generation_time:.3f} s")
    else:
        print("Generation time : 0.000 s (cached)")

    if selected_voice_id:
        print(f"Voice used      : {selected_voice_id}")

    print()

    if not args.no_play:
        print("Playing...")
        playback_time = play_audio(out_file)
        print(f"Playback time   : {playback_time:.3f} s")
    else:
        print("Playback skipped (--no-play)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)
"""Shared helpers for narrating video with Sarvam AI's Bulbul v3 text-to-speech.

Used by voice_audition.py (pick a voice) and narrate_video.py (build the
final mixed video).
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests

TTS_ENDPOINT = "https://api.sarvam.ai/text-to-speech"
MODEL = "bulbul:v3"

# bulbul:v3 rejects anything longer in a single call.
MAX_CHARS = 2500

# Bulbul v3 synthesises at 24 kHz natively; asking for more only upsamples.
NATIVE_SAMPLE_RATE = 24000

LANGUAGES = {
    "en": "en-IN", "hi": "hi-IN", "bn": "bn-IN", "ta": "ta-IN", "te": "te-IN",
    "kn": "kn-IN", "ml": "ml-IN", "mr": "mr-IN", "gu": "gu-IN", "pa": "pa-IN",
    "od": "od-IN",
}

# Voices worth auditioning for an energetic, warm "radio jockey" read over a
# factory film. Drawn from Sarvam's per-language recommendations; varun is
# deliberately excluded (docs flag it as a villain/suspense voice only).
RJ_CANDIDATES: Dict[str, List[str]] = {
    "en-IN": ["ratan", "ishita", "ashutosh", "shubh", "priya", "aditya"],
    "hi-IN": ["shubh", "ashutosh", "ratan", "aditya", "priya", "suhani"],
}

MALE_VOICES = {
    "shubh", "aditya", "rahul", "rohan", "amit", "dev", "ratan", "varun",
    "manan", "sumit", "kabir", "aayan", "ashutosh", "advait", "anand",
    "tarun", "sunny", "mani", "gokul", "vijay", "mohit", "rehan", "soham",
}
FEMALE_VOICES = {
    "ritu", "priya", "neha", "pooja", "simran", "kavya", "ishita", "shreya",
    "roopa", "tanya", "shruti", "suhani", "kavitha", "rupali",
}

# Brisk and expressive: the combination that reads as "RJ" rather than
# newsreader (flatter) or audiobook (slower).
RJ_PACE = 1.1
RJ_TEMPERATURE = 0.75


class SarvamError(RuntimeError):
    pass


def enable_utf8_output() -> None:
    """Stop the Windows console mangling Devanagari in log output."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def load_api_key(env_path: Optional[Path] = None) -> str:
    key = os.environ.get("SARVAM_API_KEY")
    if key:
        return key.strip()

    env_path = env_path or Path(__file__).with_name(".env")
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("SARVAM_API_KEY") and "=" in line:
                return line.split("=", 1)[1].strip().strip("'\"")

    raise SarvamError(
        "No Sarvam API key found. Add a line to .env:\n"
        "    SARVAM_API_KEY=your_key_here\n"
        "Get one from https://dashboard.sarvam.ai (free tier includes 1,000 credits)."
    )


def resolve_language(code: str) -> str:
    code = code.strip().lower()
    if code in LANGUAGES:
        return LANGUAGES[code]
    if code in LANGUAGES.values():
        return code
    raise SarvamError(
        "Unknown language '%s'. Use one of: %s"
        % (code, ", ".join(sorted(LANGUAGES.values())))
    )


def synthesize(
    text: str,
    speaker: str,
    language_code: str,
    api_key: str,
    pace: float = RJ_PACE,
    temperature: float = RJ_TEMPERATURE,
    sample_rate: int = NATIVE_SAMPLE_RATE,
    timeout: int = 120,
) -> bytes:
    """Render one chunk of text and return decoded WAV bytes."""
    if not text.strip():
        raise SarvamError("Refusing to synthesize empty text.")
    if len(text) > MAX_CHARS:
        raise SarvamError(
            "Text is %d characters; bulbul:v3 caps a single call at %d. "
            "Split the cue into shorter lines." % (len(text), MAX_CHARS)
        )

    payload = {
        "text": text,
        "model": MODEL,
        "language_code": language_code,
        "speaker": speaker,
        "pace": pace,
        "temperature": temperature,
        "speech_sample_rate": sample_rate,
        "output_audio_codec": "wav",
    }

    response = requests.post(
        TTS_ENDPOINT,
        headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
        timeout=timeout,
    )

    if response.status_code != 200:
        raise SarvamError(
            "Sarvam returned HTTP %d for speaker '%s':\n%s"
            % (response.status_code, speaker, response.text[:800])
        )

    body = response.json()
    audios = body.get("audios") or []
    if not audios:
        raise SarvamError("Sarvam returned no audio. Response: %s" % body)

    return base64.b64decode("".join(audios))


# --------------------------------------------------------------------------
# ffmpeg helpers
# --------------------------------------------------------------------------

def ensure_ffmpeg() -> None:
    """winget installs onto the machine PATH, which this process may predate."""
    from shutil import which

    if which("ffmpeg") and which("ffprobe"):
        return

    if sys.platform == "win32":
        extra = []
        for scope in ("Machine", "User"):
            try:
                out = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('Path','%s')" % scope],
                    capture_output=True, text=True, timeout=30,
                )
                extra.append(out.stdout.strip())
            except (OSError, subprocess.SubprocessError):
                pass
        os.environ["PATH"] = os.pathsep.join([os.environ.get("PATH", "")] + extra)

    if not (which("ffmpeg") and which("ffprobe")):
        raise SarvamError(
            "ffmpeg/ffprobe not found. Install with: winget install --id Gyan.FFmpeg -e"
        )


def run_ffmpeg(args: List[str]) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SarvamError("ffmpeg failed:\n%s" % (result.stderr or result.stdout)[:2000])


def media_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SarvamError("ffprobe failed on %s:\n%s" % (path, result.stderr))
    return float(result.stdout.strip())


def normalize_clip(src: Path, dst: Path, target_i: float = -16.0,
                   target_tp: float = -1.5, target_lra: float = 11.0) -> None:
    """Bring one clip to a target loudness using two-pass loudnorm.

    Two passes matter: measuring first lets loudnorm apply a single linear
    gain. Its one-pass mode is dynamic and would pump the quiet moments.
    """
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
         "-af", "loudnorm=I=%.2f:TP=%.2f:LRA=%.2f:print_format=json" % (
             target_i, target_tp, target_lra),
         "-f", "null", "-"],
        capture_output=True, text=True,
    )

    measured = None
    match = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", probe.stderr, re.S)
    if match:
        try:
            measured = json.loads(match[-1])
        except ValueError:
            measured = None

    if measured:
        af = ("loudnorm=I=%.2f:TP=%.2f:LRA=%.2f:measured_I=%s:measured_TP=%s:"
              "measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true:print_format=summary"
              % (target_i, target_tp, target_lra, measured["input_i"],
                 measured["input_tp"], measured["input_lra"],
                 measured["input_thresh"], measured.get("target_offset", "0.0")))
    else:
        af = "loudnorm=I=%.2f:TP=%.2f:LRA=%.2f" % (target_i, target_tp, target_lra)

    run_ffmpeg(["-i", str(src), "-af", af, "-ar", "48000", str(dst)])


def speech_bounds(path: Path, threshold_db: float = -40.0,
                  min_silence: float = 0.05) -> tuple:
    """Where the voice actually starts and stops inside a clip.

    Bulbul pads its output with a little silence, and the amount varies per
    request. Finding the real edges lets a caller time the gap between two
    clips instead of inheriting whatever padding happened to come back.
    """
    total = media_duration(path)
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "silencedetect=noise=%.1fdB:d=%.3f" % (threshold_db, min_silence),
         "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr

    starts = [float(v) for v in re.findall(r"silence_start: (-?[\d.]+)", probe)]
    ends = [float(v) for v in re.findall(r"silence_end: (-?[\d.]+)", probe)]

    spans = []
    for i, s in enumerate(starts):
        spans.append((s, ends[i] if i < len(ends) else total))

    start, end = 0.0, total
    if spans and spans[0][0] <= min_silence:
        start = spans[0][1]
    if spans and spans[-1][1] >= total - min_silence:
        end = spans[-1][0]

    if end - start < 0.05:      # all silence, or detection misfired
        return 0.0, total
    return start, end


def trim_silence(src: Path, dst: Path, threshold_db: float = -40.0) -> None:
    """Copy a clip with its leading and trailing silence removed."""
    start, end = speech_bounds(src, threshold_db)
    run_ffmpeg(["-i", str(src), "-af",
                "atrim=start=%.3f:end=%.3f,asetpts=N/SR/TB" % (start, end),
                "-ar", "48000", "-ac", "1", str(dst)])


def concat_with_gaps(segments: List[Path], gaps: List[float], dst: Path) -> None:
    """Join clips end to end, separated by exactly the given silences.

    `gaps` holds the pause after each segment except the last, so it is always
    one shorter than `segments`.
    """
    if len(segments) == 1:
        run_ffmpeg(["-i", str(segments[0]), "-ar", "48000", "-ac", "1", str(dst)])
        return

    inputs: List[str] = []
    for seg in segments:
        inputs += ["-i", str(seg)]

    parts, sequence = [], []
    for i in range(len(segments)):
        parts.append("[%d:a]aformat=sample_fmts=fltp:sample_rates=48000:"
                     "channel_layouts=mono[a%d]" % (i, i))
        sequence.append("[a%d]" % i)
        if i < len(gaps) and gaps[i] > 0.005:
            parts.append("anullsrc=r=48000:cl=mono,atrim=end=%.3f[g%d]" % (gaps[i], i))
            sequence.append("[g%d]" % i)

    parts.append("%sconcat=n=%d:v=0:a=1[out]"
                 % ("".join(sequence), len(sequence)))

    run_ffmpeg(inputs + ["-filter_complex", ";".join(parts),
                         "-map", "[out]", "-ar", "48000", "-ac", "1", str(dst)])


def atempo_chain(factor: float) -> str:
    """ffmpeg's atempo only accepts 0.5-2.0 per instance, so chain them."""
    parts = []
    remaining = factor
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append("atempo=%.6f" % remaining)
    return ",".join(parts)


# --------------------------------------------------------------------------
# Timestamped script parsing
# --------------------------------------------------------------------------

@dataclass
class Cue:
    index: int
    start: float
    end: Optional[float]
    text: str

    @property
    def slot(self) -> Optional[float]:
        if self.end is None:
            return None
        return max(0.0, self.end - self.start)


def parse_timecode(value: str) -> float:
    """Accept SS, MM:SS, HH:MM:SS, with , or . for fractional seconds."""
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if not 1 <= len(parts) <= 3:
        raise SarvamError("Cannot read timecode '%s'." % value)
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


_SRT_TIME = re.compile(
    r"^(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})"
)
# "00:12", "[00:12]", "00:12 -", "00:01:12.5 --> 00:01:20"
_LINE_TIME = re.compile(
    r"^\[?(\d{1,2}(?::\d{2}){0,2}(?:[.,]\d{1,3})?)\]?"
    r"(?:\s*-->\s*\[?(\d{1,2}(?::\d{2}){0,2}(?:[.,]\d{1,3})?)\]?)?"
    r"\s*[-–—:|)\]]?\s+(.*)$"
)


def parse_script(path: Path) -> List[Cue]:
    """Read a timestamped narration script.

    Handles SRT files and plain line-per-cue text such as:
        00:05 Welcome to Vimal Enterprises.
        00:18 --> 00:26 Kraft paper arrives in massive reels.
    """
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", raw.strip())
    cues: List[Cue] = []

    # SRT: timing line followed by one or more text lines.
    if any(_SRT_TIME.match(l.strip()) for b in blocks for l in b.splitlines()):
        for block in blocks:
            lines = [l for l in block.splitlines() if l.strip()]
            for i, line in enumerate(lines):
                match = _SRT_TIME.match(line.strip())
                if not match:
                    continue
                text = " ".join(l.strip() for l in lines[i + 1:]).strip()
                if text:
                    cues.append(Cue(len(cues) + 1,
                                    parse_timecode(match.group(1)),
                                    parse_timecode(match.group(2)),
                                    text))
                break
    else:
        for raw_line in raw.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            match = _LINE_TIME.match(line)
            if not match:
                # A continuation of the previous cue.
                if cues:
                    cues[-1].text = (cues[-1].text + " " + line).strip()
                    continue
                raise SarvamError(
                    "Line has no leading timestamp and no cue precedes it:\n  %s" % line
                )
            start, end, text = match.groups()
            if text.strip():
                cues.append(Cue(len(cues) + 1, parse_timecode(start),
                                parse_timecode(end) if end else None,
                                text.strip()))

    if not cues:
        raise SarvamError("No timestamped cues found in %s." % path)

    cues.sort(key=lambda c: c.start)
    for i, cue in enumerate(cues, 1):
        cue.index = i
    return cues

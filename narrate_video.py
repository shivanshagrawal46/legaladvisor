"""Turn a timestamped script into a narration track and lay it under a video.

    python narrate_video.py --plan --script narration.txt
    python narrate_video.py --script narration.txt --speaker ratan \
        --video "D:\\VIMAL ENTERPRISES DOCUMENTARY (compressed).mp4"

Each cue is synthesised with Sarvam Bulbul v3, placed at its timestamp, and
gently sped up if it would run past its slot. The plant's own audio is ducked
underneath the voice. Video is stream-copied, so it is never re-encoded.

Script format (see narration_example.txt):
    00:05 Welcome to Vimal Enterprises.
    00:18 --> 00:26 Kraft paper arrives in massive reels.
SRT files work too.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path
from typing import List, Optional

import sarvam_tts as st

# Leave a breath between one cue and the next so they never collide.
CUE_GAP = 0.25

# A pause may stretch this far past its nominal length when the slot allows.
PAUSE_STRETCH = 1.8
PAUSE_FLOOR = 0.14

# Bulbul's reading length varies between requests, so a cue can come back too
# long for its slot to hold both the words and their pauses. When that happens
# the words give way, not the silence: a 5% tighter read with a real pause in
# it sounds calmer than a natural read with the pause squeezed out. This is
# the share of each pause that is defended before the voice is touched.
PAUSE_GUARANTEE = 0.55


def main() -> int:
    st.enable_utf8_output()
    args = _parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        print("Script not found: %s" % script_path)
        return 1

    cues = st.parse_script(script_path)
    st.ensure_ffmpeg()

    video_path = Path(args.video) if args.video else None
    video_duration = None
    if video_path:
        if not video_path.exists():
            print("Video not found: %s" % video_path)
            return 1
        video_duration = st.media_duration(video_path)

    windows = _compute_windows(cues, video_duration)
    _print_plan(cues, windows, video_duration)

    if args.plan:
        print("\nPlan only — nothing synthesised, no credits used.")
        return 0

    api_key = st.load_api_key()
    language = st.resolve_language(args.language)

    workdir = Path(args.workdir)
    cache = workdir / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    print("\nSynthesising %d cues as '%s' (%s, pace %.2f, temperature %.2f)"
          % (len(cues), args.speaker, language, args.pace, args.temperature))

    clips: List[Path] = []
    spans: List[tuple] = []
    overruns = []
    for cue, window in zip(cues, windows):
        sys.stdout.write("  [%02d] %s  " % (cue.index, _hhmmss(cue.start)))
        sys.stdout.flush()

        pieces = _split_for_pauses(cue.text)
        kinds = [kind for _, kind in pieces[:-1]]

        # Synthesise each clause on its own and strip Bulbul's own padding,
        # so the only silence in the cue is silence we chose.
        segments = []
        for n, (segment_text, _) in enumerate(pieces):
            raw = _synth_cached(segment_text, args, language, api_key, cache)
            trimmed = workdir / ("cue_%03d_seg%02d.wav" % (cue.index, n))
            st.trim_silence(raw, trimmed)
            segments.append(trimmed)

        speech = sum(st.media_duration(s) for s in segments)
        gaps, speedup = _fit_pauses(speech, kinds, window, args)

        if speedup > 1.001:
            tightened = []
            for n, seg in enumerate(segments):
                dst = workdir / ("cue_%03d_seg%02d_fitted.wav" % (cue.index, n))
                st.run_ffmpeg(["-i", str(seg), "-filter:a",
                               st.atempo_chain(speedup), str(dst)])
                tightened.append(dst)
            segments = tightened

        staged = workdir / ("cue_%03d_joined.wav" % cue.index)
        st.concat_with_gaps(segments, gaps, staged)

        # Level each cue on its own. Normalising the assembled timeline
        # instead would drag the silence between cues up with it.
        clip = workdir / ("cue_%03d.wav" % cue.index)
        if args.no_normalize:
            shutil.copyfile(staged, clip)
        else:
            st.normalize_clip(staged, clip)

        fitted = st.media_duration(clip)
        clips.append(clip)
        spans.append((cue.start, cue.start + fitted))

        note = ""
        if gaps:
            note = "  %d pause(s) %.2f-%.2fs" % (len(gaps), min(gaps), max(gaps))
        if speedup > 1.001:
            note += "  (words %.2fx to keep them)" % speedup
        if window and fitted > window + 0.05:
            note += "  OVERRUNS by %.1fs" % (fitted - window)
            overruns.append((cue, fitted - window))
        print("%5.1fs / %4.1fs%s" % (fitted, window or 0.0, note))

    narration = Path(args.narration or (workdir / "narration_track.wav"))
    total = video_duration or (max(c.start for c in cues) + 30)
    _build_narration_track(cues, clips, narration, total, args)
    print("\nNarration track: %s  (%.1fs)" % (narration, st.media_duration(narration)))

    if overruns:
        print("\nHeads-up: %d cue(s) still run past their slot even after speeding up."
              % len(overruns))
        for cue, over in overruns:
            print("  [%02d] %s over by %.1fs — shorten the line or move the next cue later."
                  % (cue.index, _hhmmss(cue.start), over))

    if not video_path:
        print("\nNo --video given, so nothing was mixed. Pass one to produce a final cut.")
        return 0

    output = Path(args.output) if args.output else video_path.with_name(
        video_path.stem + " (narrated).mp4")
    _mix_into_video(video_path, narration, output, spans, args)

    size_mb = output.stat().st_size / (1024 * 1024)
    print("\nDone.")
    print("  %s  (%.1f MB)" % (output, size_mb))
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--script", required=True, help="Timestamped script (.txt or .srt)")
    p.add_argument("--video", help="Video to narrate; omit to only build the audio track")
    p.add_argument("--output", help="Final video path")
    p.add_argument("--narration", help="Where to write the narration-only WAV")

    p.add_argument("--speaker", default="shubh", help="Sarvam voice (default: shubh)")
    p.add_argument("--language", default="hi",
                   help="en, hi, ... (default: hi, which is also correct for Hinglish)")
    p.add_argument("--pace", type=float, default=st.RJ_PACE)
    p.add_argument("--temperature", type=float, default=st.RJ_TEMPERATURE)

    p.add_argument("--pause-long", type=float, default=0.85,
                   help="Silence inserted at '…' (default: 0.85s)")
    p.add_argument("--pause-sentence", type=float, default=0.45,
                   help="Silence inserted at a full stop (default: 0.45s)")

    p.add_argument("--max-speedup", type=float, default=1.25,
                   help="Most a cue may be sped up to fit its slot (default: 1.25)")
    p.add_argument("--voice-gain", type=float, default=0.0,
                   help="dB applied to the narration (default: 0)")
    p.add_argument("--duck", type=float, default=10.0,
                   help="dB to dip the video's own audio under the voice "
                        "(default: 10; use 0 to keep it flat)")
    p.add_argument("--music-gain", type=float, default=0.0,
                   help="dB applied to the video's own audio throughout, before "
                        "ducking (default: 0; negative sits the music lower)")
    p.add_argument("--no-normalize", action="store_true",
                   help="Skip loudness normalisation of the narration")

    p.add_argument("--plan", action="store_true",
                   help="Show cue timing and exit without calling the API")
    p.add_argument("--workdir", default="narration_build")
    return p.parse_args()


def _compute_windows(cues, video_duration) -> List[Optional[float]]:
    """How long each cue may run before it collides with the next one."""
    windows: List[Optional[float]] = []
    for i, cue in enumerate(cues):
        if cue.end is not None:
            windows.append(cue.slot)
            continue
        if i + 1 < len(cues):
            windows.append(max(0.5, cues[i + 1].start - cue.start - CUE_GAP))
        elif video_duration:
            windows.append(max(0.5, video_duration - cue.start))
        else:
            windows.append(None)
    return windows


def _print_plan(cues, windows, video_duration) -> None:
    print("Cues: %d" % len(cues))
    if video_duration:
        print("Video length: %s" % _hhmmss(video_duration))
    print()
    print("  #   start     window   chars  text")
    for cue, window in zip(cues, windows):
        window_s = "%6.1fs" % window if window else "     —"
        preview = cue.text if len(cue.text) <= 58 else cue.text[:55] + "..."
        print("  %-3d %-9s %s %6d  %s"
              % (cue.index, _hhmmss(cue.start), window_s, len(cue.text), preview))

    if video_duration:
        late = [c for c in cues if c.start >= video_duration]
        if late:
            print("\nWarning: %d cue(s) start after the video ends." % len(late))


def _split_for_pauses(text: str) -> List[tuple]:
    """Break a cue at its written pauses, tagging what each break is worth.

    Bulbul treats "…" and a full stop as little more than a comma — measured
    on this script they bought 0.2-0.5s, and twice bought nothing at all. So
    the pauses are cut out of the text and re-inserted as real silence later.
    """
    pieces: List[tuple] = []
    buffer = ""

    for i, ch in enumerate(text):
        buffer += ch
        if ch == "\u2026":
            kind = "long"
        elif ch in "\u0964.?!":
            kind = "sentence"
        else:
            continue

        if text[i + 1:].strip():        # only a pause if something follows
            pieces.append((buffer.strip(), kind))
            buffer = ""

    if buffer.strip():
        pieces.append((buffer.strip(), None))
    return pieces or [(text, None)]


def _fit_pauses(speech: float, kinds: List[str], window: Optional[float], args):
    """Pick a pause length for each break, and how much to tighten the words.

    The returned speed-up applies to the speech alone, never to the silence,
    so buying pause room never shortens the pause it was bought for.
    """
    nominal = [args.pause_long if k == "long" else args.pause_sentence
               for k in kinds]

    if window is None:
        return nominal, 1.0
    if not nominal:
        return [], min(speech / window, args.max_speedup) if speech > window else 1.0

    wanted = sum(nominal)
    defended = wanted * PAUSE_GUARANTEE

    speedup = 1.0
    if window - speech < defended:
        # The words have crowded out the silence. Tighten them just enough to
        # win the defended share back, within the cap the caller allows.
        room = window - defended
        speedup = min(speech / room, args.max_speedup) if room > 0 else args.max_speedup
        speech = speech / speedup

    budget = window - speech

    if budget >= wanted:
        # Room to spare: let the pauses open up rather than trail dead air.
        target = min(budget, wanted * PAUSE_STRETCH)
        return [p * target / wanted for p in nominal], speedup

    floor = [PAUSE_FLOOR] * len(nominal)
    if budget <= sum(floor):
        return floor, speedup

    # Shrink each pause proportionally into whatever budget is left.
    span = wanted - sum(floor)
    keep = (budget - sum(floor)) / span
    return [f + (p - f) * keep for p, f in zip(nominal, floor)], speedup


def _synth_cached(text, args, language, api_key, cache: Path) -> Path:
    fingerprint = hashlib.sha256(
        "|".join([text, args.speaker, language,
                  "%.3f" % args.pace, "%.3f" % args.temperature]).encode("utf-8")
    ).hexdigest()[:16]

    cached = cache / ("%s.wav" % fingerprint)
    if not cached.exists():
        audio = st.synthesize(text, args.speaker, language, api_key,
                              pace=args.pace, temperature=args.temperature)
        cached.write_bytes(audio)
    return cached


def _build_narration_track(cues, clips, output: Path, total: float, args) -> None:
    """Lay every clip onto one silent timeline of the full video length."""
    output.parent.mkdir(parents=True, exist_ok=True)

    inputs: List[str] = []
    for clip in clips:
        inputs += ["-i", str(clip)]

    filters = []
    for i, cue in enumerate(cues):
        delay_ms = int(round(cue.start * 1000))
        filters.append(
            "[%d:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            "adelay=%d|%d[d%d]" % (i, delay_ms, delay_ms, i)
        )

    mix_in = "".join("[d%d]" % i for i in range(len(clips)))
    # normalize=0 keeps each cue at full level instead of dividing by input count.
    filters.append("%samix=inputs=%d:duration=longest:normalize=0[mixed]"
                   % (mix_in, len(clips)))

    chain = "[mixed]apad=whole_dur=%.3f,atrim=0:%.3f" % (total, total)
    if abs(args.voice_gain) > 0.01:
        chain += ",volume=%.2fdB" % args.voice_gain
    filters.append(chain + "[out]")

    st.run_ffmpeg(inputs + ["-filter_complex", ";".join(filters),
                            "-map", "[out]", "-ar", "48000", "-ac", "2",
                            str(output)])


def _duck_expression(spans, duck_db: float, ramp: float = 0.35) -> str:
    """A gain curve that sits at 1.0, dipping to -duck_db across each cue.

    Driven by the cue timings we already know rather than by a sidechain
    compressor, so the dip is exactly the depth asked for and never triggers
    on the plant's own machinery noise.
    """
    depth = 10.0 ** (-abs(duck_db) / 20.0)

    trapezoids = []
    for start, end in spans:
        trapezoids.append(
            "min(clip((t-%.3f)/%.3f,0,1),clip((%.3f-t)/%.3f,0,1))"
            % (start - ramp, ramp, end + ramp, ramp)
        )

    envelope = trapezoids[0]
    for term in trapezoids[1:]:
        envelope = "max(%s,%s)" % (envelope, term)

    return "1-%.6f*(%s)" % (1.0 - depth, envelope)


def _mix_into_video(video: Path, narration: Path, output: Path, spans, args) -> None:
    has_audio = _has_audio_stream(video)
    print("\nMixing into video (stream-copying the picture, so no quality loss)...")

    if not has_audio:
        st.run_ffmpeg(["-i", str(video), "-i", str(narration),
                       "-map", "0:v:0", "-map", "1:a:0",
                       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", "-movflags", "+faststart", str(output)])
        return

    background = "[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    # A flat trim first, so the music sits lower everywhere; the duck then
    # takes it further down only while the voice is actually speaking.
    if abs(args.music_gain) > 0.01:
        background += ",volume=%.2fdB" % args.music_gain
    if args.duck > 0.01 and spans:
        background += ",volume=volume='%s':eval=frame" % _duck_expression(spans, args.duck)
    background += "[bg]"

    graph = background + ";[bg][1:a]amix=inputs=2:duration=first:normalize=0[aout]"

    st.run_ffmpeg(["-i", str(video), "-i", str(narration),
                   "-filter_complex", graph,
                   "-map", "0:v:0", "-map", "[aout]",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                   "-movflags", "+faststart", str(output)])


def _has_audio_stream(video: Path) -> bool:
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def _hhmmss(seconds: float) -> str:
    total = int(seconds)
    return "%02d:%02d:%05.2f" % (total // 3600, (total % 3600) // 60,
                                 seconds - (total // 60) * 60)


if __name__ == "__main__":
    raise SystemExit(main())

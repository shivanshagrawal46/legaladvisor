"""Render the same line through several Sarvam voices so you can pick one.

    python voice_audition.py --language en
    python voice_audition.py --language hi --text "..." --speakers shubh,ratan

Writes one WAV per voice into voice_samples/ plus a single stitched
comparison file with each voice announced before it speaks.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sarvam_tts as st

DEFAULT_LINES = {
    "en-IN": (
        "At Vimal Enterprises, every sheet begins as a giant reel of kraft paper. "
        "Watch closely, because in the next few seconds, this paper becomes a "
        "corrugated board strong enough to carry a hundred kilograms."
    ),
    "hi-IN": (
        "Vimal Enterprises में, हर sheet की शुरुआत होती है kraft paper के एक विशाल reel से। "
        "ध्यान से देखिए, क्योंकि अगले कुछ seconds में, यही paper बन जाता है एक ऐसा "
        "corrugated board, जो सौ किलो का वज़न आराम से उठा सकता है।"
    ),
}


def main() -> int:
    st.enable_utf8_output()

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--language", default="en",
                        help="en, hi, ta, ... or a full code like en-IN (default: en)")
    parser.add_argument("--text", help="Line to audition (defaults to a sample about the plant)")
    parser.add_argument("--script", help="Audition using a cue from a real script instead")
    parser.add_argument("--cue", type=int, default=1, help="Which cue of --script to use")
    parser.add_argument("--speakers", help="Comma-separated voices (default: the RJ shortlist)")
    parser.add_argument("--gender", choices=("male", "female", "all"), default="all",
                        help="Narrow the default shortlist to one gender")
    parser.add_argument("--pace", type=float, default=st.RJ_PACE)
    parser.add_argument("--temperature", type=float, default=st.RJ_TEMPERATURE)
    parser.add_argument("--outdir", default="voice_samples")
    args = parser.parse_args()

    language = st.resolve_language(args.language)
    api_key = st.load_api_key()
    st.ensure_ffmpeg()

    if args.script:
        cues = st.parse_script(Path(args.script))
        if not 1 <= args.cue <= len(cues):
            print("--cue must be between 1 and %d" % len(cues))
            return 1
        text = cues[args.cue - 1].text
    else:
        text = args.text or DEFAULT_LINES.get(language) or DEFAULT_LINES["en-IN"]
    if args.speakers:
        speakers = [s.strip() for s in args.speakers.split(",") if s.strip()]
    else:
        speakers = list(st.RJ_CANDIDATES.get(language, st.RJ_CANDIDATES["en-IN"]))
        if args.gender == "male":
            speakers = [s for s in speakers if s in st.MALE_VOICES]
            # The shortlist leans on the docs' picks; top up so there is a real choice.
            for extra in ("aditya", "rahul", "rohan", "amit"):
                if len(speakers) >= 6:
                    break
                if extra not in speakers:
                    speakers.append(extra)
        elif args.gender == "female":
            speakers = [s for s in speakers if s in st.FEMALE_VOICES]
            for extra in ("ishita", "ritu", "shreya", "kavya"):
                if len(speakers) >= 6:
                    break
                if extra not in speakers:
                    speakers.append(extra)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("Language   : %s" % language)
    print("Pace       : %.2f    Temperature: %.2f" % (args.pace, args.temperature))
    print("Auditioning: %s" % ", ".join(speakers))
    print("Line       : %s\n" % text)

    rendered = []
    for speaker in speakers:
        sys.stdout.write("  %-10s ... " % speaker)
        sys.stdout.flush()
        try:
            audio = st.synthesize(text, speaker, language, api_key,
                                  pace=args.pace, temperature=args.temperature)
        except st.SarvamError as exc:
            print("failed\n     %s" % exc)
            continue

        path = outdir / ("%s.wav" % speaker)
        path.write_bytes(audio)
        print("%5.1fs  %s" % (st.media_duration(path), path))
        rendered.append((speaker, path))

    if not rendered:
        print("\nNo samples were produced.")
        return 1

    _build_comparison_reel(rendered, outdir, language, api_key, args)

    print("\nOpen the folder and listen: %s" % outdir.resolve())
    print("Then pass your pick to narrate_video.py with --speaker <name>.")
    return 0


def _build_comparison_reel(rendered, outdir, language, api_key, args) -> None:
    """Stitch every sample into one file, each announced by name."""
    reel = outdir / "_all_voices.wav"
    pieces = []

    for speaker, path in rendered:
        try:
            # Announce in a neutral, flat read so it can't be mistaken for the sample.
            intro = st.synthesize("Voice: %s." % speaker, speaker, language,
                                  api_key, pace=1.0, temperature=0.3)
            intro_path = outdir / ("_intro_%s.wav" % speaker)
            intro_path.write_bytes(intro)
            pieces.append(intro_path)
        except st.SarvamError:
            pass
        pieces.append(path)

    inputs = []
    for piece in pieces:
        inputs += ["-i", str(piece)]

    # Half a second of silence between clips so they don't run together.
    filters = []
    for i in range(len(pieces)):
        filters.append("[%d:a]aresample=24000,apad=pad_dur=0.5[a%d]" % (i, i))
    concat = "".join("[a%d]" % i for i in range(len(pieces)))
    filters.append("%sconcat=n=%d:v=0:a=1[out]" % (concat, len(pieces)))

    try:
        st.run_ffmpeg(inputs + ["-filter_complex", ";".join(filters),
                                "-map", "[out]", str(reel)])
        print("\nCombined reel: %s" % reel)
    except st.SarvamError as exc:
        print("\nCould not build the combined reel: %s" % exc)
    finally:
        for piece in pieces:
            if piece.name.startswith("_intro_"):
                piece.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())

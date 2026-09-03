"""Build a labelled A/B reel of the opening 24 seconds in four treatments."""
import subprocess
import sys
from pathlib import Path

import sarvam_tts as st

st.enable_utf8_output()
st.ensure_ffmpeg()

MASTER = r"D:\VIMAL ENTERPRISES DOCUMENTARY (compressed).mp4"
SOURCE = r"D:\_ab_source.mp4"
FONT = "_inter_semibold.ttf"

VARIANTS = [
    ("A", "_ab_v0_current.txt",   "shubh",    1.00, "A  CURRENT - shubh, pace 1.0, commas"),
    ("B", "_ab_v1_pauses.txt",    "shubh",    0.90, "B  PAUSES  - shubh, pace 0.9, trimmed"),
    ("C", "_ab_v1_pauses.txt",    "ashutosh", 0.90, "C  PAUSES  - ashutosh, pace 0.9, trimmed"),
    ("D", "_ab_v2_spacious.txt",  "ashutosh", 0.85, "D  SPACIOUS- ashutosh, pace 0.85, deeper trim"),
]

if not Path(SOURCE).exists():
    print("Cutting the 24s source segment...")
    st.run_ffmpeg(["-ss", "0", "-t", "24", "-i", MASTER,
                   "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "24", "-c:a", "aac", "-b:a", "160k", SOURCE])
print("Source: %s (%.1fs)\n" % (SOURCE, st.media_duration(Path(SOURCE))))

labelled = []
for tag, script, speaker, pace, label in VARIANTS:
    print("=" * 70)
    print("%s  %s | %s | pace %.2f" % (tag, script, speaker, pace))
    print("=" * 70)

    out = r"D:\_ab_%s.mp4" % tag
    cmd = [sys.executable, "narrate_video.py",
           "--script", script, "--speaker", speaker, "--language", "hi",
           "--pace", "%.2f" % pace, "--temperature", "0.7",
           "--duck", "14", "--max-speedup", "1.10",
           "--video", SOURCE, "--output", out,
           "--workdir", "_ab_build_%s" % tag]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    for line in (result.stdout or "").splitlines():
        if line.startswith("  [") or "OVERRUN" in line or "Heads-up" in line:
            print(line)
    if result.returncode != 0:
        print("FAILED:\n%s" % (result.stderr or "")[-1500:])
        continue

    # Burn a caption so the clips stay identifiable once concatenated.
    tagged = r"D:\_ab_%s_lbl.mp4" % tag
    drawtext = ("drawtext=fontfile=%s:text='%s':fontcolor=white:fontsize=30:"
                "box=1:boxcolor=black@0.65:boxborderw=14:x=40:y=40"
                % (FONT, label.replace(":", "\\:").replace(",", "\\,")))
    st.run_ffmpeg(["-i", out, "-vf", drawtext, "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "24", "-c:a", "aac", "-b:a", "160k", tagged])
    labelled.append(tagged)
    print()

if labelled:
    inputs = []
    for path in labelled:
        inputs += ["-i", path]
    filters = []
    for i in range(len(labelled)):
        filters.append("[%d:v]setsar=1[v%d];[%d:a]aresample=48000[a%d]" % (i, i, i, i))
    concat = "".join("[v%d][a%d]" % (i, i) for i in range(len(labelled)))
    filters.append("%sconcat=n=%d:v=1:a=1[v][a]" % (concat, len(labelled)))

    reel = r"D:\_AB_opening_comparison.mp4"
    st.run_ffmpeg(inputs + ["-filter_complex", ";".join(filters),
                            "-map", "[v]", "-map", "[a]",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                            "-c:a", "aac", "-b:a", "160k",
                            "-movflags", "+faststart", reel])
    size = Path(reel).stat().st_size / (1024 * 1024)
    print("Comparison reel: %s  (%.1f MB, %.0fs)"
          % (reel, size, st.media_duration(Path(reel))))

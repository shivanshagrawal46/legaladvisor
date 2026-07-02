"""Count lines of code across the system, by language, excluding deps/build."""
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_DIRS = {"node_modules", "__pycache__", ".git", "dist", ".venv", "venv",
                ".pytest_cache", ".mypy_cache", "build", ".idea", ".vscode"}
EXT_LANG = {
    ".py": "Python", ".jsx": "React JSX", ".js": "JavaScript",
    ".ts": "TypeScript", ".tsx": "React TSX", ".css": "CSS",
    ".html": "HTML", ".md": "Markdown", ".json": "JSON",
    ".sh": "Shell", ".yml": "YAML", ".yaml": "YAML",
}

by_lang = defaultdict(lambda: [0, 0, 0])  # files, lines, blank
# also split: app code vs throwaway scratch (_*.py / scripts starting with _)
app_py_lines = scratch_py_lines = 0

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
    for fn in filenames:
        ext = os.path.splitext(fn)[1].lower()
        lang = EXT_LANG.get(ext)
        if not lang:
            continue
        fp = os.path.join(dirpath, fn)
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            continue
        nlines = len(lines)
        nblank = sum(1 for ln in lines if not ln.strip())
        by_lang[lang][0] += 1
        by_lang[lang][1] += nlines
        by_lang[lang][2] += nblank
        if ext == ".py":
            if fn.startswith("_"):
                scratch_py_lines += nlines
            else:
                app_py_lines += nlines

print("=" * 64)
print(f"{'LANGUAGE':16s} {'FILES':>8s} {'LINES':>10s} {'CODE(non-blank)':>16s}")
print("=" * 64)
tot_f = tot_l = tot_c = 0
for lang, (f, l, b) in sorted(by_lang.items(), key=lambda x: -x[1][1]):
    code = l - b
    tot_f += f; tot_l += l; tot_c += code
    print(f"{lang:16s} {f:>8,} {l:>10,} {code:>16,}")
print("-" * 64)
print(f"{'TOTAL':16s} {tot_f:>8,} {tot_l:>10,} {tot_c:>16,}")
print("=" * 64)

# code-only languages (exclude md/json/yaml/html/css to get pure source)
CODE_LANGS = {"Python", "React JSX", "JavaScript", "TypeScript", "React TSX", "Shell"}
src_f = sum(by_lang[k][0] for k in CODE_LANGS if k in by_lang)
src_l = sum(by_lang[k][1] for k in CODE_LANGS if k in by_lang)
print(f"PURE SOURCE CODE (py/js/jsx/ts/sh): {src_f:,} files, {src_l:,} lines")
print(f"  Python app code (non _-scratch): {app_py_lines:,} lines")
print(f"  Python scratch/_audit code:      {scratch_py_lines:,} lines")

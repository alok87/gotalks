#!/usr/bin/env python3
"""Report every slide that overflows, not just the first one.

presenterm's --validate-overflows aborts at the first offender, so this splits
the deck into one-slide decks and validates each independently. Prints the slide
number, its source line range, its title, and the widest line it contains.

usage: ./audit-slides.py [--cols N] [--rows N] [deck.md]
"""
import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[_\]P][^\x1b\x07]*(?:\x07|\x1b\\)")
# presenterm reserves columns for the slide's left/right padding
PADDING = 10


def validate(path: pathlib.Path, cols: int, rows: int) -> str:
    r = subprocess.run(
        [
            sys.executable, str(HERE / "ptyrun.py"),
            "--cols", str(cols), "--rows", str(rows), "--timeout", "60", "--",
            "presenterm", "--image-protocol", "ascii-blocks",
            "--validate-overflows", "--validate-snippets", str(path),
        ],
        capture_output=True, text=True,
    )
    out = ANSI.sub("", r.stdout + r.stderr).replace("\r", "").replace("\0", "")
    # match presenterm's own diagnostics only - rendered slide text also
    # contains words like "error", which is not a failure
    m = re.search(
        r"presentation overflows \w+ on slide \d+"
        r"|Error loading presentation: [^\n]*"
        r"|invalid command: [^\n]*",
        out,
    )
    return m.group(0).strip() if m else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cols", type=int, default=120)
    ap.add_argument("--rows", type=int, default=40)
    ap.add_argument("deck", nargs="?", default=str(HERE / "talks" / "go-software-design.md"))
    args = ap.parse_args()

    src = pathlib.Path(args.deck).read_text()
    fm = re.match(r"^---\n.*?\n---\n", src, re.S)
    front, body = (fm.group(0), src[fm.end():]) if fm else ("", src)

    slides, start = [], 0
    for m in re.finditer(r"^<!-- end_slide -->\n?", body, re.M):
        slides.append((body[start:m.start()], start))
        start = m.end()
    if body[start:].strip():
        slides.append((body[start:], start))

    base_line = front.count("\n")
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for i, (text, off) in enumerate(slides, 1):
            f = pathlib.Path(td) / f"s{i}.md"
            f.write_text(front + text)
            err = validate(f, args.cols, args.rows)
            if not err:
                continue
            bad += 1
            first = base_line + body[:off].count("\n") + 1
            title = next(
                (l.lstrip("# ").strip() for l in text.split("\n") if l.startswith("#")),
                "(no title)",
            )
            lines = text.split("\n")
            widest = max(lines, key=len)
            print(f"slide {i:>2}  line {first:<5}  {title}")
            print(f"          {err}")
            print(f"          lines={len(lines)} (limit ~{args.rows - 7})"
                  f"  widest={len(widest)} (limit ~{args.cols - PADDING}): {widest[:90]!r}")
    print(f"\n{len(slides)} slides, {bad} overflowing at {args.cols}x{args.rows}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

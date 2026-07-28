#!/usr/bin/env python3
"""Render each `+exec` slide for real and assert the hidden lines are not on screen.

presenterm's Go hidden-line prefix is `/// ` (Rust uses `# `). Getting it wrong is
invisible to snippet validation - the code still runs, it just prints the prefix
markers to your audience. So this renders the actual slide through a pty and greps
the pixels-as-text for anything that should have been hidden.

usage: ./check-hidden.py [deck.md ...]
"""
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[_\]P][^\x1b\x07]*(?:\x07|\x1b\\)")


def render(md: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "one.md"
        # no frontmatter: the slide under test is slide 1, so it renders immediately
        f.write_text(md)
        r = subprocess.run(
            [sys.executable, str(HERE / "ptyrun.py"),
             "--cols", "120", "--rows", "40", "--timeout", "30", "--",
             "presenterm", "--image-protocol", "ascii-blocks", str(f)],
            capture_output=True, text=True,
        )
    return ANSI.sub("", r.stdout + r.stderr).replace("\r", "").replace("\0", "")


def main() -> int:
    decks = sys.argv[1:] or [str(HERE / "talks" / "go-software-design.md")]
    bad = 0
    for deck in decks:
        src = pathlib.Path(deck).read_text()
        blocks = list(re.finditer(r"^```go \+exec[^\n]*\n(.*?)^```", src, re.S | re.M))
        print(f"{pathlib.Path(deck).name}: {len(blocks)} exec snippets")
        for i, m in enumerate(blocks, 1):
            body = m.group(1)
            hidden = [l[4:].strip() for l in body.split("\n") if l.startswith("/// ")]
            visible = " ".join(
                l for l in body.split("\n") if not l.startswith("/// ")
            )
            # a hidden line whose text also occurs in the visible code cannot be
            # distinguished on screen, so it proves nothing either way
            distinctive = [h for h in hidden if h and h not in visible]
            stray = [l for l in body.split("\n") if l.strip() in ("#", "///")]
            screen = render(f"# exec snippet {i}\n\n```go +exec\n{body}```\n")
            flat = " ".join(screen.split())

            leaked = [h for h in distinctive if h in flat]
            markers = "///" in flat or re.search(r"(?<!\S)# ", flat)
            ok = not leaked and not markers and not stray
            bad += 0 if ok else 1
            print(f"  snippet {i}: {'ok' if ok else 'LEAK'}"
                  f"  ({len(hidden)} hidden, {len(distinctive)} checkable)")
            for h in leaked:
                print(f"      visible on screen but should be hidden: {h!r}")
            if markers:
                print("      a prefix marker (/// or #) is being rendered literally")
            for l in stray:
                print(f"      bare prefix line renders literally: {l!r}")
    print("\n" + ("all hidden lines are hidden" if not bad else f"{bad} snippet(s) leaking"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

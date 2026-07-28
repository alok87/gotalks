#!/usr/bin/env bash
# Verifies the deck:
#   1. presenterm parses it and no slide overflows a 120x40 terminal
#   2. every ```go block is syntactically valid Go
#   3. every ```go +exec block actually runs
#   4. hidden snippet lines are really hidden in the rendered slide
#
# Slide snippets are fragments, so before parsing each block is normalised:
#   - an inline `package x` clause is used instead of a synthetic one
#   - `...` elisions (`f(a, ...)`, `{ ... }`) are filled in
#   - top-level declarations and loose statements are separated, and the loose
#     statements are wrapped in a function body
#   - presenterm's Go hidden-line prefix (`/// `) is stripped, as presenterm does
# Blocks are parsed, not type-checked, so a snippet may reference identifiers
# that live on a different slide.
# Editing gotchas for the decks (measured against presenterm 0.16 at 120x40):
#   - speaker_note comment bodies are YAML: keep them single-quoted ('' escapes ')
#   - code lines <= 84 chars; code blocks and blockquotes never wrap
#   - inside a [1,1] column_layout: bullets <= 48 chars, code lines <= 46
#   - hidden +exec setup lines use the Go prefix `/// ` (a bare /// renders)
set -uo pipefail

DECK="${1:-$(dirname "$0")/talks/go-software-design.md}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== presenterm parse + layout validation (120x40)"
# presenterm needs a real terminal even to validate, and stops at the first
# offending slide, so audit-slides.py drives it through a pty one slide at a time
python3 "$(dirname "$0")/audit-slides.py" --cols 120 --rows 40 "$DECK"
LAYOUT_STATUS=$?
echo

echo "== go snippet syntax check"
python3 - "$DECK" "$WORK" <<'PY'
import re, subprocess, sys, pathlib

deck, work = sys.argv[1], pathlib.Path(sys.argv[2])
src = pathlib.Path(deck).read_text()

DECL_KW = ("func ", "func(", "type ", "var ", "const ", "import ", "//go:")


def unhide(code):
    """Strip presenterm's Go hidden-line prefix: `/// ` lines run but are not shown."""
    return "\n".join(
        l[4:] if l.startswith("/// ") else l for l in code.split("\n")
    )


def fill_elisions(code):
    code = re.sub(r"\{\s*\.\.\.\s*\}", "{}", code)      # elided body/composite literal
    code = re.sub(r",\s*\.\.\.\s*\)", ")", code)        # f(a, ...)
    code = re.sub(r"\(\s*\.\.\.\s*\)", "()", code)      # f(...)
    code = re.sub(r"(?<![\w\]\)])\.\.\.(?![\w\[])", "nil", code)  # bare ..., not p... or ...T
    return code


def split_decls(code):
    """Separate top-level declarations from loose statements by brace depth."""
    decls, loose, pending = [], [], []
    depth, in_decl = 0, False
    for line in code.split("\n"):
        stripped = line.lstrip()
        if depth == 0 and not in_decl:
            in_decl = stripped.startswith(DECL_KW)
            target = pending if (stripped.startswith("//") or not stripped) else None
            if target is not None:
                pending.append(line)          # comments attach to whatever follows
                continue
        bucket = decls if in_decl else loose
        bucket.extend(pending)
        pending.clear()
        bucket.append(line)
        depth += line.count("{") + line.count("(") - line.count("}") - line.count(")")
        if depth <= 0:
            depth, in_decl = 0, False
    decls.extend(pending)
    return "\n".join(decls), "\n".join(loose)


def parses(code, name):
    f = work / name
    f.write_text(code)
    r = subprocess.run(["gofmt", "-e", str(f)], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


blocks = [
    (src[: m.start()].count("\n") + 1, m.group(1).strip(), m.group(2))
    for m in re.finditer(r"^```go([^\n]*)\n(.*?)^```", src, re.S | re.M)
]

fail = 0
for i, (line, attrs, body) in enumerate(blocks):
    body = fill_elisions(unhide(body))
    pkg = re.search(r"^package \w+$", body, re.M)
    if pkg:
        # splice out by span, not by replace: the same text often appears in a comment
        header = pkg.group(0)
        body = body[: pkg.start()] + body[pkg.end() :]
    else:
        header = "package p"

    decls, loose = split_decls(body)
    shapes = [
        f"{header}\n{decls}\nfunc _() {{\n{loose}\n}}\n",
        f"{header}\n{body}\n",
        f"{header}\nfunc _() {{\n{body}\n}}\n",
        f"{header}\ntype _ struct {{\n{body}\n}}\n",
        f"{header}\ntype _ interface {{\n{body}\n}}\n",
    ]
    errs = []
    for n, s in enumerate(shapes):
        ok, err = parses(s, f"b{i}_{n}.go")
        if ok:
            break
        errs.append(err)
    else:
        fail += 1
        print(f"  FAIL line {line} (attrs={attrs!r})")
        print("    " + errs[0].replace("\n", "\n    "))

print(f"  {len(blocks)} go blocks checked, {fail} unparseable")
sys.exit(1 if fail else 0)
PY
GO_STATUS=$?
echo

echo "== runnable (+exec) snippets"
python3 - "$DECK" "$WORK" <<'PY'
import re, subprocess, sys, pathlib

deck, work = sys.argv[1], pathlib.Path(sys.argv[2])
src = pathlib.Path(deck).read_text()
n, bad = 0, 0
for m in re.finditer(r"^```go\s+\+exec[^\n]*\n(.*?)^```", src, re.S | re.M):
    n += 1
    f = work / f"exec{n}.go"
    f.write_text("\n".join(  # presenterm runs `/// ` lines but does not display them
        l[4:] if l.startswith("/// ") else l
        for l in m.group(1).split("\n")
    ))
    r = subprocess.run(["go", "run", str(f)], capture_output=True, text=True)
    ok = r.returncode == 0
    bad += 0 if ok else 1
    print(f"  snippet {n}: {'ok' if ok else 'FAIL'}")
    print("    " + (r.stdout + r.stderr).strip().replace("\n", "\n    "))
print(f"  {n} exec snippets, {bad} failing")
sys.exit(1 if bad else 0)
PY
EXEC_STATUS=$?
echo

echo "== hidden lines are actually hidden on screen"
python3 "$(dirname "$0")/check-hidden.py" "$DECK"
HIDDEN_STATUS=$?
echo

if (( LAYOUT_STATUS || GO_STATUS || EXEC_STATUS || HIDDEN_STATUS )); then
  echo "FAILED (layout=$LAYOUT_STATUS syntax=$GO_STATUS exec=$EXEC_STATUS hidden=$HIDDEN_STATUS)"
  exit 1
fi
echo "all checks passed"

# Go Software Design - a terminal talk for SDEs

A ~1-hour, example-heavy [presenterm](https://github.com/mfontanini/presenterm) deck on how to
design Go: deep modules, composition vs inheritance, interfaces, packages, dependency injection,
and errors. Written for engineers arriving from OOP languages.

Distilled from the canon - every opinion traces to a source (cited on the last slide):
John Ousterhout's *A Philosophy of Software Design*, Rob Pike's *Go Proverbs*, Dave Cheney's
*Practical Go* and *SOLID Go Design*, Peter Bourgon, Kat Zien, Mat Ryer, Bill Kennedy's
package-oriented design, and alok87.in's posts on singletons and interface rules.

## Run it

```sh
brew install presenterm             # or: cargo install presenterm
presenterm -x go-software-design.md # -x enables the two live-runnable snippets
```

Keys you need on stage:

| Key | Action |
| --- | --- |
| `space`, `→`, `j`, `l` | next (also advances one `pause` reveal at a time) |
| `←`, `k`, `h` | back |
| `n` / `p` | next/previous slide, skipping the pauses |
| **`Ctrl+E`** | **run the code snippet on screen** (the two `+exec` slides) |
| `<number>G` | jump to slide; `gg` first, `G` last |
| `Ctrl+P` | slide index |
| `Ctrl+R` | reload the file after an edit |
| `?` | key bindings, `esc` closes it |
| `q` | quit |

Speaker notes are on every slide - most of the explanation lives there, so read them once
before presenting, or run them on a second screen:

```sh
presenterm -x --publish-speaker-notes go-software-design.md   # projector
presenterm --listen-speaker-notes go-software-design.md       # your laptop
```

**Terminal size: at least 120x40.** Code blocks and tables do not wrap. Zoom out with `cmd -`
until you have 120 columns; verify with `tput cols; tput lines`.

Export a handout:

```sh
presenterm --export-html -o deck.html go-software-design.md
presenterm --export-pdf go-software-design.md    # needs: pip install weasyprint
```

## What it covers

52 slides: 42 content + 9 part dividers + title. Dividers carry a time budget
(`Part 4 · 10 min`) so you can tell mid-talk whether you're behind. Budgets sum to 60 min -
a full hour with no slack; the self-contained slides to skip if running long are *How to
carve a new package*, *Small interfaces compose*, *SOLID*, and *The review card* (it works
as a handout).

| Part | Min | Topics |
| --- | --- | --- |
| 1 | 5 | **A small door to a big room** - Ousterhout's deep modules, `io.Writer`, deep vs shallow `Store`, information leakage |
| 2 | 10 | **Composition, not inheritance** - Go's toolbox, embedding is a field + a generated forwarder, the receiver is the inner value (live demo), interfaces for dispatch, wrapping, embedding good/bad |
| 3 | 10 | **Interfaces** - implicit satisfaction, accept interfaces/return structs, ask for the least, compose small interfaces client-side, discover don't design, the typed-nil trap (live demo) |
| 4 | 10 | **Packages** - the package as Go's unit of design, naming as capability, how to carve one, dismantling `utils`, the `boot.Database` singleton story, no package state, zero values + `internal/`, thin `main`, by feature not by layer |
| 5 | 7 | **Dependencies** - DI is parameters, build in layers at the top, the option pattern when constructors grow, fake only the seams |
| 6 | 7 | **Errors** - values, handle once, add context with `%w`, `errors.Is`/`As`, define errors out of existence |
| 7 | 6 | **Testing** - table-driven tests, fakes over mock frameworks, the `testing` toolkit (`t.Helper`, `t.Parallel`, `-race`) |
| 8 | 5 | **Zooming out** - SOLID mapped to Go, naming in one slide, concurrency in one slide, six takeaways, the review card, sources |

Two slides run live (`+exec`, needs `-x`, press `Ctrl+E`):

- **embedding has no dispatch** - `u.Retries()` returns 0 but `u.Call()` prints `receiver=main.Gateway retries=3`
- **the typed-nil error** - `err == nil` is `false` for a returned nil `*MyErr`

## Verify before presenting

```sh
./verify.sh go-software-design.md
```

Checks four things and exits non-zero on any failure:

1. **Layout** - drives presenterm through a pty, one slide at a time, and reports *every* slide
   that overflows 120x40 (presenterm itself stops at the first one).
2. **Go syntax** - extracts every ```go block and parses each with `gofmt -e`. Snippets are
   fragments, so each is normalised first (inline `package` clause, `...` elisions filled,
   declarations split from loose statements, `/// ` hidden-line prefix stripped).
3. **Runnable snippets** - `go run`s every `+exec` block and prints its output.
4. **Hidden lines** - renders each `+exec` slide for real and greps the screen to prove the
   hidden setup lines aren't visible. Go's hidden-line prefix is `/// ` (Rust's is `# `);
   using the wrong one still *runs* fine, so nothing but a render catches it.

Helper scripts:

| Script | Use |
| --- | --- |
| `verify.sh <deck>` | run all four checks |
| `audit-slides.py --cols N --rows N <deck>` | list every overflowing slide with line number and widest line |
| `check-overflow.sh COLS ROWS <deck>` | quick whole-deck check at an arbitrary size |
| `check-hidden.py <deck>` | renders every `+exec` slide and asserts `/// ` lines are off-screen |
| `ptyrun.py` | runs a command under a fixed-size pty and answers terminal capability probes; presenterm blocks without this |

## Editing notes

Things that will bite you if you modify the deck:

- **Comment commands are YAML.** `<!-- speaker_note: text with: a colon -->` fails to parse.
  All notes are single-quoted; keep them that way (`''` escapes an inner apostrophe).
- **Code lines must be ≤ 84 chars** at 120 columns - code blocks never wrap. Blockquotes don't
  wrap either. Prose paragraphs and tables do.
- **Inside a `column_layout`, list items do not wrap** - hard limit **48 chars per bullet**
  (46 for code lines) in a `[1, 1]` split at 120 columns, measured. Plain paragraphs in the
  same column wrap fine.
- **Hiding setup lines in a `+exec` snippet: the Go prefix is `/// `**, with the trailing
  space. A bare `///` renders literally.
- Slides are separated by `<!-- end_slide -->`; `<!-- pause -->` reveals incrementally.
- Re-run `./verify.sh go-software-design.md` after any edit.

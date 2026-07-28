# gotalks

Terminal talks, built with [presenterm](https://github.com/mfontanini/presenterm).

## Talks

| Talk | About |
| --- | --- |
| [Go Software Design](talks/go-software-design.md) | ~1 hr. Deep modules, composition vs inheritance, interfaces, packages, DI, errors, testing. For SDEs arriving from OOP languages. |

The talk files are plain markdown - GitHub renders them readable as-is
(presenterm directives like `<!-- pause -->` are invisible comments).

## Present

```sh
brew install presenterm
presenterm -x talks/go-software-design.md   # -x enables the live-runnable snippets
```

Needs a terminal of at least **120x40**. `Ctrl+E` runs the code on the two demo slides.
Speaker notes: `presenterm -x --publish-speaker-notes <talk>` on the projector,
`presenterm --listen-speaker-notes <talk>` on your laptop.

## Verify after editing

```sh
./verify.sh talks/go-software-design.md
```

Gates: slide layout at 120x40, `gofmt -e` on every snippet, `go run` on every `+exec`
block, and a render check that `/// ` hidden lines stay hidden. Editing gotchas
(YAML speaker notes, 84-char code lines, 46-char code lines inside columns) are
documented in `verify.sh`'s header.

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
./verify.sh
```

# gotalks

Terminal talks, built with [presenterm](https://github.com/mfontanini/presenterm).

## Talks

| Talk | About |
| --- | --- |
| [Go Software Design](talks/go-software-design.md) | ~1 hr. Deep modules, composition vs inheritance, interfaces, packages, DI, errors, testing. |

The talk files are plain markdown - GitHub renders them readable as-is
(presenterm directives like `<!-- pause -->` are invisible comments).

## Run

```sh
brew install presenterm
presenterm -x talks/go-software-design.md
```

Terminal must be at least 120x40. `Ctrl+E` runs the code on the demo slides.

## Verify after editing

```sh
./verify.sh
```

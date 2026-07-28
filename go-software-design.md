---
title: "Go Software Design"
sub_title: "How to write Go that stays simple as it grows"
author: "Alok Kumar Singh"
theme:
  name: catppuccin-macchiato
---

# What this hour is about

Not Go syntax. **How to design Go code** so it is still easy to change next year.

<!-- pause -->

Six ideas:

1. Hide a lot behind a little.
2. Embedding is not inheritance.
3. Ask for the smallest thing you need.
4. A package is named for what it *does*.
5. Pass dependencies in. Never reach out for them.
6. Errors are values. Add context, handle once.

<!-- pause -->

Stop me any time. Questions are better than notes.

<!-- speaker_note: 'Audience is mostly SDE1s, so keep the pace slow and check in. None of this is mine: John Ousterhout A Philosophy of Software Design, Rob Pike Go Proverbs, Dave Cheney Practical Go and SOLID Go Design, Peter Bourgon Go for Industrial Programming, Kat Zien on structure, Mat Ryer on HTTP services. Sources on the last slide.' -->

<!-- end_slide -->

# What "good design" means here

<!-- pause -->

## Simple

Few moving parts. Not *clever*, not *short* - **few things to hold in your head**.

<!-- pause -->

## Readable

The next person can see what it does without asking you. That person is you, in six months.

<!-- pause -->

## Boring

If you are choosing between an interesting solution and a boring one, pick boring.

<!-- pause -->

> "Clear is better than clever." - Go Proverbs

<!-- speaker_note: 'Dijkstra: simplicity is a prerequisite for reliability. Readable code is reliable code because you can SEE the bug. Every strange-looking Go decision - no inheritance, no exceptions, unused imports being errors - is one of these three winning an argument. Come back to this slide whenever someone misses a feature from another language.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 1 · 5 min
---
# A small door to a big room

<!-- end_slide -->

# The one design idea to remember

> A module's **cost** is its interface. Its **benefit** is what it does for you.
> - John Ousterhout, *A Philosophy of Software Design*

<!-- pause -->

So the best thing you can build is a **small door to a big room**:

```go
type Writer interface {
    Write(p []byte) (int, error)
}
```

**One method.** Behind that door: files, network sockets, gzip compression,
in-memory buffers, HTTP responses, `os.Stdout`.

<!-- pause -->

> "The bigger the interface, the weaker the abstraction." - Go Proverbs

Same idea, found twice. Small door, big room. Ousterhout calls it a **deep module**.

<!-- speaker_note: 'This slide is the spine of the whole talk - everything later is an application of it. Cost is what a caller has to learn and what you can never change again; benefit is how much work you saved them. io.Writer is the deepest module in Go: one method, tens of thousands of implementations. The opposite is a shallow module: 40 methods that each do almost nothing, so the caller has to learn all 40 and you saved them nothing.' -->

<!-- end_slide -->

# Small door, big room - or a wall of doors

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Deep

```go
type Store interface {
    Save(o Order) error
    Get(id string) (Order, error)
}
```

Behind it: SQL, retries, caching,
connection pooling, metrics.

**2 things to learn.**

<!-- column: 1 -->

## Shallow

```go
type Store interface {
    BeginTx() (*sql.Tx, error)
    QueryRow(q string) *sql.Row
    Exec(q string, a ...any) error
    // ... 22 more
}
```

Behind it: almost nothing. It
just forwards to `database/sql`.

**25 things to learn.**

<!-- reset_layout -->

<!-- pause -->

The shallow one also **leaks**: every caller now knows you use SQL, so you can never
stop using SQL. That is the cost of a big door.

<!-- speaker_note: 'This is the single most common design mistake in review. The shallow version feels safer because it is flexible, but it moved all the thinking to the caller and locked in the database. Ousterhout calls the sql.Tx in the signature information leakage: one decision - we use Postgres - is now visible in every file that touches a Store.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 2 · 10 min
---
# Composition, not inheritance

<!-- end_slide -->

# Go has no classes. Here is what it has.

Structs, methods, interfaces, functions, packages. That is the whole toolbox.

<!-- pause -->

No `class`. No `extends`. No `implements`. No `super`. No `this`. No exceptions.

<!-- pause -->

| | |
| --- | --- |
| Want to **group data**? | a struct |
| Want to **add behaviour**? | a method |
| Want to **swap implementations**? | an interface |
| Want to **reuse another type's code**? | put it inside yours |

<!-- pause -->

All four, in the standard library you already use:

```go
type Buffer struct {                      // group data: a struct    (bytes)
    buf []byte
}

func (b *Buffer) Write(p []byte) (int, error)   // add behaviour: a method

type Writer interface {                   // swap implementations    (io)
    Write(p []byte) (int, error)
}

type ReadWriter struct {                  // reuse: put it inside yours (bufio)
    *Reader
    *Writer
}
```

<!-- pause -->

**If it has the methods, it fits.** No declaration anywhere. And nothing ever inherits fields.

<!-- speaker_note: 'Ask who has written Java. Be kind about it - they will reach for a hierarchy for the first month, and that is normal. The last line is the big one: in Java a class fits an interface only if the author wrote implements when writing the class. In Go, a type fits because it HAS the method. The snippet is the proof from the stdlib: bytes.Buffer has Write, so it IS an io.Writer - bytes never imports io to say so. And bufio.ReadWriter is real stdlib code reusing Reader and Writer by embedding them. One snippet, three packages, zero declarations.' -->

<!-- end_slide -->

# Embedding: a field you don't have to name

```go
type Gateway struct{ Name string }

func (Gateway) Retries() int   { return 3 }
func (g Gateway) Call() string { return fmt.Sprint(g.Retries()) }
```

<!-- pause -->

```go
type UPI struct {
    Gateway        // no field name, so the type name IS the name
    VPA string
}
```

<!-- pause -->

The inner type's fields and methods are **promoted** to the outer type:

```go
u.Name          // promoted field   (same as u.Gateway.Name)
u.Call()        // promoted method  (same as u.Gateway.Call())
u.VPA           // UPI's own field
```

<!-- speaker_note: 'Read it aloud as: a UPI HAS a Gateway, and you get to skip the field name. Both spellings are the same field - u.Name and u.Gateway.Name. Nothing is copied and nothing is inherited: there is one Gateway value sitting inside one UPI value. Promotion is a spelling convenience, and that is genuinely the whole feature.' -->

<!-- end_slide -->

# The one rule: the method runs on the inner value

For every promoted method, the compiler writes you a small forwarder:

```go
func (u UPI) Call() string { return u.Gateway.Call() }   // written for you
```

<!-- pause -->

Now suppose `UPI` defines its own `Retries()`, and `Gateway.Call()` calls `Retries()`:

| you write | what actually runs |
| --- | --- |
| `u.Retries()` | `u.Retries()` - UPI's method |
| `u.Call()` | `u.Gateway.Call()` - which calls **Gateway's** `Retries()` |

<!-- pause -->

Look at the `.Gateway.` in the middle. You called the method **on the Gateway field**,
so of course it uses Gateway's methods.

<!-- speaker_note: 'This is the one semantic they must leave with. Effective Go says it exactly: when we embed a type, the methods become methods of the outer type, but when they are invoked the receiver is the inner type, not the outer one. Promotion is spelling, not dispatch. If someone asks how Java differs: Java this carries the object real type so the call dispatches back down to the subclass. Do not use the phrase virtual dispatch unless they ask.' -->

<!-- end_slide -->

# See it run

```go +exec
/// package main
/// import "fmt"
/// type Gateway struct{ Name string }
/// func (Gateway) Retries() int { return 3 }
/// type UPI struct {
/// 	Gateway
/// 	VPA string
/// }
/// func (UPI) Retries() int { return 0 }
func (g Gateway) Call() string {
	return fmt.Sprintf("receiver=%T retries=%d", g, g.Retries())
}

func main() {
	u := UPI{Gateway: Gateway{Name: "upi"}, VPA: "a@b"}
	fmt.Println("u.Retries() ->", u.Retries())
	fmt.Println("u.Call()    ->", u.Call())
}
```

<!-- pause -->

```text
u.Retries() -> 0                                 ← UPI's method
u.Call()    -> receiver=main.Gateway retries=3   ← Gateway's, as promised
```

<!-- speaker_note: 'Ctrl+E to run it. Ask them to predict first - most will say retries=0. The %T prints the receiver type, which is the proof: it really is a Gateway inside Call. Say the practical version out loud: if you want UPI to change what Call does, embedding will not do it. Next slide shows what does.' -->

<!-- end_slide -->

# Want the behaviour to change? Use an interface.

Same `UPI` as before - but now `Call` **asks for behaviour** instead of embedding:

```go
type Retrier interface{ Retries() int }

func Call(r Retrier) string {
    return fmt.Sprintf("receiver=%T retries=%d", r, r.Retries())
}
```

<!-- pause -->

Put both versions next to each other:

```text
u.Call()   -> receiver=main.Gateway retries=3   embedding: the inner value
Call(u)    -> receiver=main.UPI     retries=0   interface: the WHOLE value
```

You passed the **whole UPI**, so `Retries()` is UPI's. That is the difference:
embedding forwards to a field; an interface carries your actual type.

<!-- pause -->

Then add behaviour by **wrapping** - one small layer at a time:

```go
type loggingStore struct {
    Store                 // embedded interface: every method forwarded
    log *slog.Logger
}

func (s loggingStore) Save(o Order) error {
    err := s.Store.Save(o)
    s.log.Info("save", "order", o.ID, "err", err)
    return err
}
```

One method written, and `loggingStore` is a full `Store`.

<!-- speaker_note: 'Two mechanisms, both compose. Interfaces give you the swap; wrapping gives you layers. loggingStore still compiles when you add a method to Store tomorrow, because the embedded interface forwards it - that is why this beats writing all five methods by hand. Same trick gives test doubles with no mock framework. Cheney: Go types are open for extension but closed for modification - you can add and wrap, but you cannot reach in and change.' -->

<!-- end_slide -->

# Embedding: use it, don't abuse it

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good

```go
type Order struct {
    Timestamps  // shared fields,
                // exposed on purpose
    ID string
}
```

```go
type loggingStore struct {
    Store       // decorate 1 method
}
```

<!-- column: 1 -->

## Bad

```go
type Order struct {
    BaseModel  // fake inheritance
    Utils      // grab-bag of helpers
}
```

```go
type Registry struct {
    sync.Mutex // Lock() is now
               // your public API
}
```

<!-- reset_layout -->

<!-- pause -->

One question decides it: **would you list the embedded type in this type's docs, as
part of what callers may use?** Yes, embed it. No, give it a name: `mu sync.Mutex`.

<!-- speaker_note: 'Left: shared audit fields is the classic good embed, and embedding an interface to decorate one method is the best use in the language. Right: BaseModel expecting an override silently uses the inner method - we just proved that; Utils makes every helper part of your public surface; and the mutex one is subtle but real - any caller can now lock your internals forever and you can never remove it without breaking them. Anything you embed is yours to support forever.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 3 · 10 min
---
# Interfaces

<!-- end_slide -->

# Nobody declares anything

```go
// package fmt
type Stringer interface{ String() string }
```

```go
// your package - no import of fmt, no "implements"
type Money struct{ Paise int64 }

func (m Money) String() string {
    return fmt.Sprintf("₹%d.%02d", m.Paise/100, m.Paise%100)
}
```

<!-- pause -->

`Money` is now a `fmt.Stringer`. It never says so.

<!-- pause -->

Two consequences worth sitting with:

- The **caller** decides what it needs. The type being used doesn't know it exists.
- You can write an interface **today** that types written **years ago** already satisfy.

<!-- speaker_note: 'The most important design decision in the language. Because there is no implements keyword, there is no dependency arrow from the implementation to the abstraction, which is what keeps Go import graphs shallow and refactors cheap. Concrete demo if they look blank: add String() to a type and fmt.Println immediately formats it differently - you imported nothing and declared nothing.' -->

<!-- end_slide -->

# Accept interfaces, return structs

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good

```go
func Save(w io.Writer,
    d *Doc) error
```

Works with a file, a buffer,
an HTTP response, gzip.
Easy to test.

```go
func NewStore(
    db *sql.DB) *PgStore
```

Caller sees every method
and the real doc page.

<!-- column: 1 -->

## Bad

```go
func Save(f *os.File,
    d *Doc) error
```

Caller must have a real file
on disk. Hard to test. And
you can `Seek` and `Close` it.

```go
func NewStore(
    db *sql.DB) Store
```

Adding a method is now
a breaking change.

<!-- reset_layout -->

<!-- pause -->

**Be flexible about what you take in. Be specific about what you hand back.**

<!-- speaker_note: 'Accepting io.Writer is a smaller door: you ask for less, so more things fit through. Returning the concrete type is the opposite direction on purpose - give the caller everything and let THEM narrow it to an interface if they want one. The one exception: return an interface when the concrete type must stay unexported, like errors.New returning error.' -->

<!-- end_slide -->

# Ask for the least you need

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good

```go
type userGetter interface {
    Get(ctx context.Context,
        id string) (User, error)
}

func Welcome(g userGetter,
    id string) error
```

Test double: **4 lines.**

The signature says
*this cannot write*.

<!-- column: 1 -->

## Bad

```go
type Database interface {
    GetUser(...)
    SaveUser(...)
    GetOrder(...)
    // ... 36 more
}

func Welcome(db Database,
    id string) error
```

Test double: **39 lines.**

<!-- reset_layout -->

<!-- pause -->

The good interface is **unexported and local** - it exists for this one function,
declared right next to it.

<!-- speaker_note: 'This is the small-door idea applied to a single function. The interface lives in the package that CALLS it, not the package that implements it - that is the habit to build. And notice it is lowercase: it is not part of anyone API, it is just this function saying what it needs.' -->

<!-- end_slide -->

# Small interfaces compose into big ones

The stdlib builds everything from one-method pieces:

```go
type Reader interface{ Read(p []byte) (int, error) }
type Closer interface{ Close() error }

type ReadCloser interface {   // embedding: Reader + Closer
    Reader
    Closer
}
```

<!-- pause -->

Your code can do the same - and the **client** does the composing:

```go
// package user defines the small ones
type Getter interface{ Get(id string) (User, error) }
type Creater interface{ Create(u User) error }
```

```go
// the client composes exactly what IT needs
type userReadWriter interface {
    user.Getter
    user.Creater
}
```

<!-- pause -->

**Build small parts. Compose the bigger whole.** Name them verb + `-er`: `Reader`,
`Notifier`, `Getter`. Never `IUser`, never `UserInterface`.

<!-- speaker_note: 'This is the answer to "but my service really does need 6 methods" - fine, compose it from the small ones at the point of use. Composing interfaces has no shadowing puzzle because there is no implementation to shadow: it is just set union on method sets. Naming: one-method interfaces get the method name plus -er, per Effective Go. The I prefix and Interface suffix are Java habits.' -->

<!-- end_slide -->

# Write the type first. Find the interface later.

A shape you will see in code review:

```text
user/
  service.go          type UserService interface { ... }
  service_impl.go     type userServiceImpl struct { ... }
  mock_service.go     // generated
```

Three files, one implementation, zero flexibility gained.

<!-- pause -->

> Write the **concrete type** first. Add an interface when you get a **second
> implementation**, or at a real boundary: network, clock, filesystem, database.

<!-- pause -->

If an interface has exactly **one implementation and one generated mock**, it is not
a design - it is a testing workaround. Usually the fix is a smaller function signature.

<!-- speaker_note: 'The fight you will have most often in review, so give them the test question: does a second implementation plausibly exist in production? If no, delete the interface. Ousterhout has a related habit called design it twice - write it two ways before you commit; in Go that often means writing the concrete type and only then seeing what the interface should be. Also flag the naming: Impl suffix and IFoo prefix are not Go.' -->

<!-- end_slide -->

# One trap worth knowing

```go +exec
/// package main
/// import "fmt"
/// type MyErr struct{}
/// func (e *MyErr) Error() string { return "boom" }
func find() *MyErr { return nil } // nil: no error

func doWork() error {
	return find() // looks harmless
}

func main() {
	err := doWork()
	fmt.Println("err == nil ?", err == nil)
	fmt.Printf("value inside: %v\n", err)
}
```

<!-- pause -->

An interface holds **two things**: a type and a value. It is `nil` only when **both** are.
`find()` returned a nil `*MyErr` - which still has a type - so the interface is not nil.

**Rule: write `error` as the return type, and `return nil` on the happy path.**

<!-- speaker_note: 'Ctrl+E. Everyone hits this exactly once, usually in production, and it reads as: the function said it worked but the caller saw an error. Do not go deeper into interface internals than the two-things sentence - that is enough to avoid it.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 4 · 10 min
---
# Packages

<!-- end_slide -->

# The package is Go's unit of design

> "Each Go package is itself a small Go program - a single unit of change,
> with a single responsibility." - Dave Cheney

<!-- pause -->

The package is where Go puts **everything** that other languages spread around:

| The unit of... | In Go |
| --- | --- |
| privacy | lowercase = package-private. There is nothing else |
| compilation | packages build and cache independently |
| change | a fix ships as a new version of one package |
| reuse | you import a package, never a class or a file |
| **design** | so this is where design happens |

<!-- pause -->

**Think in packages: write each one as if it were a small library, with one job,
that another team might import.**

<!-- speaker_note: 'This is the reframe for people who think in classes: in Go the class-shaped questions - what is public, what changes together, what can I reuse - are all answered at the package boundary. Corollary: your architecture IS the import graph. It is acyclic because the compiler refuses cycles, and a healthy one is wide and flat - many small-ish leaf packages, few tall towers. If a package cannot do anything without dragging in a friend, the boundary is in the wrong place.' -->

<!-- end_slide -->

# Name a package for what it does

Finish this sentence: *"this package lets you..."*

| Package | ...lets you |
| --- | --- |
| `net/http` | speak HTTP |
| `strconv` | turn strings into numbers and back |
| `payment` | take and refund a payment |

<!-- pause -->

| Package | ...lets you? |
| --- | --- |
| `models` | ...contains structs. |
| `utils` | ...contains functions. |
| `common` | ...contains whatever two packages both needed. |

<!-- pause -->

If the name describes a **kind of code** instead of a **capability**, it is the wrong package.

<!-- speaker_note: 'A package name is the first thing every caller reads, forever - the cheapest thing to get right, the most annoying to change. Ousterhout has a name for the opposite failure, classitis: lots of small modules that each do almost nothing. Go pushes the other way - fewer, larger packages - because the package is the unit of privacy, and splitting only creates exported API you did not want.' -->

<!-- end_slide -->

# How to carve a new package

Four questions before you `mkdir`:

<!-- pause -->

**1. What does it *provide*?** If the answer is "it contains the models", stop.

<!-- pause -->

**2. Could it stand alone?** A good package makes sense as a tiny library:
`clock`, `httpx`, `payment`. If it only works glued to its siblings, it is one
package pretending to be two.

<!-- pause -->

**3. Are you importing just to share a struct?** Don't. Move the shared *type*
down into a small leaf package that imports nothing.

<!-- pause -->

**4. Who knows the specifics?** Push them **up** the import graph. `main` knows
it is Postgres and Kafka; `payment` only knows its `Store` and `Notifier`
interfaces. Leaves stay abstract, the top does the choosing.

<!-- speaker_note: 'Question 3 is Bill Kennedy: question imports for the sake of sharing existing types - packages should not exist merely to share data structures. Question 4 is dependency inversion in Go clothing, and it is why main.go looks like a big constructor call: all the concrete choices live in one file at the top. One more guideline if asked: siblings at the same level should generally not import each other - if they must, one of them is really below the other.' -->

<!-- end_slide -->

# `utils` is where code goes to hide

```text
internal/utils/
  utils.go        ← 1400 lines
  string_utils.go
  constants.go    ← 200 unrelated constants
```

How it happens: *"I needed this in two places and there was an import cycle, so: utils."*

<!-- pause -->

Take each function and look at **who calls it**:

1. **One caller** → move it there, make it lowercase. Done.
2. **Many callers, one topic** → it belongs to that topic's package.
3. **Many callers, no topic** → a real library. Name it for the type it works on:
   `strings`, `slices`, `httpx`.
4. **Import cycle** → the cycle is the actual bug. Move the shared *type* down into
   a package that imports nothing.

<!-- pause -->

End state: `validate.go` sits next to the thing it validates.

<!-- speaker_note: 'Do not let them leave thinking utils is a style preference - it is a design smell with a mechanical fix, and this list is the fix. Why it hurts: a package with no topic has no reason to change together, so every unrelated change touches it and everything depends on it.' -->

<!-- end_slide -->

# Singletons: the invisible input

```go
package boot

var Database *db.Db   // the singleton

func InitDatabase(cfg db.Config) { Database = db.NewDb(cfg) }
```

<!-- pause -->

Now you join the team and write your first test:

```go
func TestRocketLaunch(t *testing.T) {
    r := NewRocket("falcon")
    if err := r.Launch(); err != nil {   // panic: nil pointer
        t.Error(err)
    }
}
```

**Nothing in `NewRocket(name string)` said it needs a database.** It secretly
reaches into `boot.Database`. That is magic - and magic is what makes code
unmaintainable.

<!-- pause -->

The `boot` package then grows: `InitKafka`, `InitCache`, `InitWorker`...
Now initialization *order* matters, and **every** package imports `boot`.

<!-- speaker_note: 'This is a real story, not a hypothetical - a function whose signature promises a string and delivers a nil-pointer panic because a global was not initialised. The design smell to name: the function behaviour is secretly altered by a variable initialised somewhere else. And the boot package becomes the centre of the import graph, which is exactly backwards - specifics belong at the top, in main, not in a package everything depends on.' -->

<!-- end_slide -->

# Don't keep state in a package

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good

```go
type Service struct {
    db *sql.DB
}

func New(db *sql.DB) *Service {
    return &Service{db: db}
}

func (s *Service) Capture(
    id string) error {
    // s.db is right there
}
```

<!-- column: 1 -->

## Bad

```go
var db *sql.DB

func Init(d *sql.DB) { db = d }

func Capture(id string) error {
    // where did db come from?
}
```

Tests can't run in parallel.
Nothing enforces `Init`.
You can never have two.

<!-- reset_layout -->

<!-- pause -->

A package-level `var` is an **invisible argument** to every function in the package.
Put it on the struct that needs it. Same rule kills `init()`. Parse flags in `main`.

<!-- speaker_note: 'The killer practical reason for an SDE1 is tests: with a global, two tests fight over the same value, so no t.Parallel and order starts to matter. With a struct, every test builds its own Service and they are independent.' -->

<!-- end_slide -->

# Two small habits

## Make the zero value work

```go
var buf bytes.Buffer   // ready to write, no constructor
var mu sync.Mutex      // ready to lock
```

Design your types so `var x Thing` is already useful, or give them a `New`.

<!-- pause -->

## Put new code in `internal/`

```text
myservice/
  cmd/myservice/main.go
  internal/            ← no other repo can import this
    payment/
    gateway/
```

The compiler enforces it. That is what lets you rename and refactor freely for years.

<!-- pause -->

`cmd/` and `internal/` are real conventions. `pkg/` is not - everything is a package.

<!-- speaker_note: 'Zero value removes a whole class of bug: nobody can forget to call your constructor. A nil slice appends fine, a nil map reads fine. On internal: default to putting new packages there and promote them out only when another repo genuinely needs them.' -->

<!-- end_slide -->

# Keep `main` tiny, group by feature

```go
func main() {
    if err := run(context.Background(), os.Args, os.Stdout); err != nil {
        fmt.Fprintln(os.Stderr, "error:", err)
        os.Exit(1)
    }
}
```

`main` can't be tested and can't return an error. `run` is an ordinary function -
your test calls it directly with a `bytes.Buffer`.

<!-- pause -->

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good: by feature

```text
payment/
review/
storage/
http/
```

<!-- column: 1 -->

## Careful: by layer

```text
handlers/
models/
storage/
```

<!-- reset_layout -->

Layers group code by **when it runs**, not by **what it knows** - so every feature
edits three packages, and `models` becomes the package everything depends on.

<!-- speaker_note: 'main-to-run is Mat Ryer. The structure point is Kat Zien plus Ousterhout: layered structure is what Ousterhout calls temporal decomposition - organising by the order things happen rather than by the knowledge each part holds. Say this gently, because layered is what most of our repos look like, and flat is a fine place for a small service to start. The advice: start flat, group by feature, let real pain move you.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 5 · 7 min
---
# Dependencies

<!-- end_slide -->

# Pass what you need. Never reach for it.

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good

```go
func New(s Store,
    c Clock) *Service {
    return &Service{
        store: s,
        clk:   c,
    }
}
```

Forget one → **compile error**,
pointing at the line.

<!-- column: 1 -->

## Bad

```go
var store *Store

func init() {
    store = mustStore()
}
```

```go
db := ctx.Value("db").(*sql.DB)
```

Forget one → **panic**, at
startup or at 3am.

<!-- reset_layout -->

<!-- pause -->

That is all "dependency injection" means in Go: **the things a type needs are
arguments to its constructor.** No framework, no container, no annotations.

<!-- speaker_note: 'Bourgon: DI is a tool for read comprehension - just enumerate dependencies as parameters. The test: if a missing dependency is a compile error you did it right; if it is a runtime panic you moved the check later for no benefit. Also flag context here: ctx is for cancellation, deadlines and request-scoped values like a trace id - it is not a bag to carry your database in.' -->

<!-- end_slide -->

# Build in layers, once, at the top

*"But then I'd have to pass `db` through every layer!"* - no. Each layer takes
only the layer **below it**:

```go
func main() {
    cfg := config.New(env)
    db  := storage.New(cfg.Database)

    repo    := user.NewRepo(db)        // only the repo sees db
    service := user.NewService(repo)   // only sees the repo
    server  := user.NewServer(service) // only sees the service
}
```

<!-- pause -->

`db` appears **once**. Nothing is passed *through* - each object holds what it
needs and hands its neighbour something smaller.

<!-- pause -->

The accepted exceptions: **loggers, metrics, tracers.** Config is not one -
break it into parts (`cfg.Database`, `cfg.Server`) and pass each where it belongs.

<!-- speaker_note: 'This slide kills the number-one objection to removing globals. The trick is that the dependency does not travel - it stops at the layer that uses it. main reads top to bottom like a recipe and the whole dependency graph is on one screen. On the exceptions: observability is ambient by nature, so a package-level slog default is a reasonable trade; some teams inject it anyway, both are defensible. Config gets no such pass: a giant config global is just the boot package wearing a suit.' -->

<!-- end_slide -->

# When constructors grow: the option pattern

Ten parameters, eight of them optional? Don't do this:

```go
srv := server.New("host", 8080, time.Minute, 120, nil, nil, true, false)
```

<!-- pause -->

```go
type Option func(*Server)

func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}

func New(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second} // defaults first
    for _, opt := range opts {
        opt(s)
    }
    return s
}
```

```go
srv := server.New(":8080",
    server.WithTimeout(time.Minute),
    server.WithMaxConn(120),
)
```

<!-- pause -->

**Required things are positional. Optional things are options, with defaults.**
If `New()` panics without `WithStore(...)`, the store was not optional.

<!-- speaker_note: 'The pattern is Rob Pike, self-referential functions, 2012 - and every major Go library uses it: grpc.Dial, zap, otel. Read the call site: it names every setting, skips what it does not care about, and never has a mystery nil in position five. The last line is the trap to warn about: options are for OPTIONAL knobs - hiding a required dependency in an option converts a compile error into a runtime panic. Builder pattern is the same idea with chaining; in Go, options are the more idiomatic of the two.' -->

<!-- end_slide -->

# Fake only the seams

```go
type Clock interface{ Now() time.Time }

type fakeClock struct{ t time.Time }

func (c *fakeClock) Now() time.Time          { return c.t }
func (c *fakeClock) Advance(d time.Duration) { c.t = c.t.Add(d) }
```

"Expires after 15 minutes" is now a **unit test**, not a `time.Sleep(15 * time.Minute)`.

<!-- pause -->

Worth injecting: **time · randomness and IDs · network · filesystem · database.**

Everything else - your own pure logic - needs nothing. If you can't say what you
would replace it with, don't take it as a parameter.

<!-- pause -->

One place in your program - `run()` - knows how everything is built. Everything
below it just receives what it needs.

<!-- speaker_note: 'Injecting a pure function is ceremony, and SDE1s over-inject once they learn the pattern, so this slide is mostly a brake. The composition root is the payoff: one function assembles the program, so you can read the whole dependency graph in one place instead of hunting through init functions.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 6 · 7 min
---
# Errors

<!-- end_slide -->

# Errors are values

```go
type error interface {
    Error() string
}
```

That is the whole thing. Not a special mechanism - **a value** you can inspect,
wrap, compare, store in a struct, or send on a channel.

<!-- pause -->

The cost: `if err != nil` everywhere.

The benefit: **every way this code can fail is visible in the code you are reading.**
Nothing jumps somewhere else invisibly.

<!-- speaker_note: 'Name the trade honestly because they will have heard the complaint. In a language with exceptions you cannot see the failure paths by reading a function; in Go you can. That is the readability principle from slide two, paid for in keystrokes.' -->

<!-- end_slide -->

# Handle an error exactly once

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good

```go
if err != nil {
    return fmt.Errorf(
        "save order: %w", err)
}
```

Add context, return.
Someone above logs it once.

<!-- column: 1 -->

## Bad

```go
if err != nil {
    log.Println("save:", err)
    return err
}
```

Now the caller logs it too.
And its caller.

One failure, five log lines,
no way to connect them.

<!-- reset_layout -->

<!-- pause -->

> **Log at the boundary. Add context in the middle. Never both.**

The boundary is your HTTP handler, your worker loop, or `main`. That is where it
gets logged, once, with everything attached.

<!-- speaker_note: 'Cheney: you may make exactly one decision about an error - handle it, wrap and return it, or log it. Doing two is the bug. If they push back with "but I want to know it happened here", the answer is the next slide: the wrapped message tells you exactly where it happened.' -->

<!-- end_slide -->

# Always say which operation failed

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

## Good

```go
return fmt.Errorf(
    "get order %s: %w", id, err)
```

```text
http: capture handler:
get order pay_123:
dial tcp: i/o timeout
```

You can read the whole story.

<!-- column: 1 -->

## Bad

```go
return err
```

```text
dial tcp: i/o timeout
```

Which order? Which caller?
Which of the nine places
that dial something?

<!-- reset_layout -->

<!-- pause -->

Style: **lowercase, no full stop, no "failed to"** - the caller adds its own prefix.
Use `%w`, not `%v`, so the error underneath stays reachable.

<!-- speaker_note: 'One fmt.Errorf per layer and the final message reads like a stack trace made of sentences. %w keeps the wrapped error reachable for errors.Is and errors.As on the next slide; %v flattens it to text and cuts the chain. Reading your own error message top-down is the fastest review check there is.' -->

<!-- end_slide -->

# Ask what happened. Don't read the message.

```go
var ErrNotFound = errors.New("order not found")
```

```go
if errors.Is(err, order.ErrNotFound) {
    http.Error(w, "not found", http.StatusNotFound)
}
```

<!-- pause -->

When you need **data** out of the error, not just its identity:

```go
var rl *RateLimitError
if errors.As(err, &rl) {
    time.Sleep(rl.RetryAfter)
}
```

<!-- pause -->

**Never** this:

```go
if strings.Contains(err.Error(), "duplicate") { ... }   // breaks on any reword
```

<!-- speaker_note: 'Simple split: Is asks WHICH error this is, As asks GIVE IT TO ME so I can read a field off it. Both see through %w wrapping, which is the whole reason to use %w. Error strings are written for humans - the moment someone improves the wording, string matching breaks silently in production.' -->

<!-- end_slide -->

# Best of all: design the error away

Ousterhout calls this **defining errors out of existence**.

<!-- pause -->

```go
// four identical checks, hiding what the code actually does
_, err := fmt.Fprintf(w, "HTTP/1.1 %d %s\r\n", st.Code, st.Reason)
if err != nil {
    return err
}
// ... and again for every header, the blank line, and the body
```

<!-- pause -->

```go
sc := bufio.NewScanner(r)
for sc.Scan() {        // returns bool, not (line, error)
    lines++
}
return lines, sc.Err() // one check, after the loop
```

The stdlib does this for you: `Scanner` remembers the first error so your loop
doesn't have to ask every time.

<!-- speaker_note: 'Ousterhout chapter is literally titled Define Errors Out Of Existence, and Cheney gives the Go version: do not get better at handling errors, design so there are fewer. Scanner is the example they already use daily without noticing. The hand-written version of the same trick is a small type wrapping io.Writer that remembers the first error - sticky errors - worth sketching on a whiteboard if asked.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 7 · 6 min
---
# Testing

<!-- end_slide -->

# Table-driven tests: the Go default

One test body, many cases. Adding a case is adding a row.

```go
func TestTruncate(t *testing.T) {
    tests := map[string]struct {
        in   string
        n    int
        want string
    }{
        "shorter than limit": {in: "hi", n: 5, want: "hi"},
        "exactly at limit":   {in: "hello", n: 5, want: "hello"},
        "over the limit":     {in: "hello!", n: 5, want: "hello"},
        "zero limit":         {in: "hi", n: 0, want: ""},
    }

    for name, tc := range tests {
        t.Run(name, func(t *testing.T) {
            got := Truncate(tc.in, tc.n)
            if got != tc.want {
                t.Errorf("Truncate(%q, %d) = %q, want %q",
                    tc.in, tc.n, got, tc.want)
            }
        })
    }
}
```

<!-- speaker_note: 'Three things to point at. The map: case names become subtest names, so a failure reads TestTruncate/zero_limit and you can run exactly one case with go test -run "TestTruncate/zero". No assertion library: got, want, t.Errorf is the whole convention - the stdlib way scales and everyone can read it. And the edge cases are ROWS, so the review question "did you test zero?" is answered by scanning the table. For struct comparisons, cmp.Diff from go-cmp is the one external helper worth knowing.' -->

<!-- end_slide -->

# Fakes, not mock frameworks

You already did the hard part - the function asks for a **small interface**:

```go
type userGetter interface {
    Get(ctx context.Context, id string) (User, error)
}
```

<!-- pause -->

So the test double is four lines. No codegen, no framework, no DSL:

```go
type fakeGetter struct {
    user User
    err  error
}

func (f fakeGetter) Get(context.Context, string) (User, error) {
    return f.user, f.err
}
```

<!-- pause -->

```go
err := Welcome(fakeGetter{err: ErrNotFound}, "u1")   // failure case: trivial
```

<!-- pause -->

If the fake is painful to write, the message is not "use mockgen" -
it is **"my interface is too big."** The pain is design feedback.

<!-- speaker_note: 'This closes the loop with part 3: small interfaces exist FOR this moment. A generated mock with expectation DSLs tests how the code talks; a fake tests what the code does - and the fake survives refactors that reorder calls. When someone reaches for mockgen because the interface has 14 methods, the fix is upstream. Fakes with a bit of state - a map-backed in-memory store - are fine too and often nicer than per-test stubs.' -->

<!-- end_slide -->

# The testing toolkit, in one slide

| | |
| --- | --- |
| `t.Run(name, ...)` | subtests: name every case, run one with `-run` |
| `t.Helper()` | first line of every test helper - failures point at the caller |
| `t.Parallel()` | free speedup - and it *proves* your code has no globals |
| `t.TempDir()` | a real directory, cleaned up for you |
| `t.Cleanup(fn)` | defer for tests - runs even when subtests fail |
| `go test -race ./...` | in CI, always. Races are invisible until 3am |

<!-- pause -->

Note what `t.Parallel()` just bought you: it only works because there is
**no package-level state**. Testability was the design lesson all along.

<!-- speaker_note: 'Do not read the table - point at t.Parallel and make the callback to the singleton slide: if your tests cannot run in parallel, you have a global, and now you know where. t.Helper is the one nobody knows: without it, a failing assertion helper reports the line inside the helper instead of the test that called it. Close with: none of these require a library. The stdlib testing package is a deep module.' -->

<!-- end_slide -->

<!-- jump_to_middle -->

Part 8 · 5 min
---
# Zooming out

<!-- end_slide -->

# You already know SOLID. Here it is in Go.

| | The principle | The Go spelling |
| --- | --- | --- |
| **S** | one reason to change | one package, one purpose - `utils` fails this |
| **O** | open for extension, closed for modification | extend by **wrapping**; you can't reach into a type |
| **L** | implementations must be substitutable | small interfaces make substitution trivial |
| **I** | don't force methods on clients | **accept the smallest interface you need** |
| **D** | depend on abstractions | import graph points **up**: `main` picks Postgres, `payment` sees only `Store` |

<!-- pause -->

Nothing new on this slide - every row is a slide you already saw.
Go doesn't make you memorise SOLID. **The language defaults push you into it.**

<!-- speaker_note: 'Dave Cheney SOLID Go Design, GolangUK 2016 - worth watching in full. The point to land: in Java, SOLID is discipline you apply against the grain of the language; in Go, implicit interfaces, no inheritance, and the acyclic import graph mean the compiler is quietly enforcing most of it. If they remember one row, make it I: accept the smallest interface - it is the one they can apply in their next PR.' -->

<!-- end_slide -->

# Naming, in one slide

| Bad | Good | Why |
| --- | --- | --- |
| `usersMap` | `users` | the type is already in the declaration |
| `currentItemValue` | `v` | 2-line scope: 1 letter is clearer |
| `pac` | `ErrPaymentAlreadyCaptured` | used far away, so spell it out |
| `payment.PaymentService` | `payment.Service` | you always read `pkg.Name` |
| `u.GetName()` | `u.Name()` | no `Get` prefix in Go |
| `MAX_RETRIES` | `MaxRetries` | Go uses MixedCaps |
| `UserServiceImpl` | `postgresUsers` | say what it *is*, not that it's an impl |

<!-- pause -->

One rule underneath all of it: **the further a name travels from where it is
declared, the longer it should be.**

<!-- speaker_note: 'Cheney: the greater the distance between a name declaration and its uses, the longer the name should be. Loop variable that lives two lines: one letter. Package-level exported error: spell the whole thing out. Also: single-method interfaces are verb plus -er - Reader, Writer, Notifier - and receivers get one or two letters, the SAME letters on every method of the type.' -->

<!-- end_slide -->

# Concurrency, in one slide

Goroutines are a **design** tool, not a speed tool. Adding them to slow code
usually makes it slower and always makes it harder to read.

<!-- pause -->

Two rules that prevent most incidents:

1. **Never start a goroutine without knowing how it stops.** If you can't answer
   *what makes this return, and who waits for it* - that is a leak.
2. **Don't decide concurrency for your caller.** Return a slice, not a channel.

<!-- pause -->

```go
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(8)                    // bounded: don't overload your own database
for _, id := range ids {
    g.Go(func() error { return process(ctx, id) })
}
return g.Wait()                  // first error cancels the rest
```

<!-- pause -->

`go test -race ./...` in CI, always. A mutex protects **data**; a channel hands
**ownership** over.

<!-- speaker_note: 'The unbounded version of that loop - go for every row of a query - is a real outage shape, so SetLimit is the line to point at. If asked about concurrency vs parallelism: concurrency is how the program is structured, parallelism is things literally running at once; a concurrent program is still correct on one CPU.' -->

<!-- end_slide -->

# Six things to take away

<!-- pause -->

**1.** Build a **small door to a big room**. The interface is the cost; what's
behind it is the benefit.

<!-- pause -->

**2.** **Embedding is not inheritance.** The method runs on the inner value.

<!-- pause -->

**3.** **Ask for the least you need.** Discover interfaces; don't design them upfront.

<!-- pause -->

**4.** **Name a package for what it does.** No `utils`, no package-level state.

<!-- pause -->

**5.** **Pass dependencies in.** If a missing one isn't a compile error, move it earlier.

<!-- pause -->

**6.** **Errors are values.** Add context, handle once, design the error away when you can.

<!-- pause -->

> "Clear is better than clever."

<!-- end_slide -->

# The review card - quote these in PRs

| One-liner | Where it came from |
| --- | --- |
| The bigger the interface, the weaker the abstraction | Go Proverbs |
| Accept interfaces, return structs | Part 3 |
| Never create an interface until you need it | Part 3 |
| Name a package for what it provides, not what it contains | Part 4 |
| A package-level `var` is an invisible argument | Part 4 |
| If a missing dependency isn't a compile error, move it earlier | Part 5 |
| Required = positional. Optional = options | Part 5 |
| Log at the boundary, add context in the middle, never both | Part 6 |
| Ask what happened (`errors.Is`), don't read the message | Part 6 |
| If the fake is painful, the interface is too big | Part 7 |
| Never start a goroutine without knowing how it stops | Part 8 |
| Clear is better than clever | Go Proverbs |

<!-- pause -->

Screenshot this one.

<!-- speaker_note: 'The whole talk in twelve quotable lines - tell them these are legitimate review comments, with a slide behind each one if anyone asks why. Then move on; do not read the table aloud.' -->

<!-- end_slide -->

# Where all of this came from

| Read / watch | Who |
| --- | --- |
| **A Philosophy of Software Design** (the book, ~170 pages) | John Ousterhout |
| **Go Proverbs** · `go-proverbs.github.io` | Rob Pike |
| **Practical Go** · `dave.cheney.net/practical-go` | Dave Cheney |
| **SOLID Go Design** | Dave Cheney |
| **Go for Industrial Programming** | Peter Bourgon |
| **How Do You Structure Your Go Apps?** | Kat Zien |
| **How I write HTTP services after 13 years** | Mat Ryer |

<!-- pause -->

If you read exactly two things: **Effective Go** (`go.dev/doc/effective_go`), then
**Go Code Review Comments** (`go.dev/wiki/CodeReviewComments`).

Between them they settle most review comments you will ever give or get.

<!-- end_slide -->

<!-- jump_to_middle -->

Thank you
---
# Questions. Arguments welcome.

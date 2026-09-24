# pbui

A terminal listener that keeps live objects in its history. Printed
names are presentations of files, directories, and processes. A click
hands the object to the next command.

See the [pbui user guide](docs/user-guide.md) for commands, interaction tips,
and a short smoke test.

The guiding influences are Ciccarelli's *Presentation Based User
Interfaces* (AITR-794), the Genera Dynamic Lisp Listener, the McKay,
York, and McMahon paper on Dynamic Windows (UIST 1989), and the CLIM
and McCLIM listeners. [`AGENTS.md`](AGENTS.md) says what each one is
for. They guide discussion. The accepted specification is the law for
implementation.

Design for each exploration lives under
`docs/design/implementation/<name>/`: a charter, a spec, and a
`checkpoints/` folder. The program lives at this project root. Create
it, its environment, and its dependencies with uv only.
[`AGENTS.md`](AGENTS.md) is that rule too.

| Exploration | What it is | Status |
|---|---|---|
| [`listener`](docs/design/implementation/listener/README.md) | First listener: `ls`, `ps`, `show`, `cd`, `rm`, `kill` | Implemented through listener 005 |
| [`listings`](docs/design/implementation/listings/README.md) | Tables, an action menu, and sort and filter on `ls` and `ps` | Implemented through listings 008 |
| [`repl`](docs/design/implementation/repl/README.md) | Python evaluation and a generic value presentation | Implemented through repl 001 |
| [`chips`](docs/design/implementation/chips/README.md) | Click a history value into the Python expression being typed | Implemented through chips 001 |
| [`sympy`](docs/design/implementation/sympy/README.md) | Pretty SymPy expressions and simplify, expand, factor | Implemented through sympy 000 |
| [`transcript`](docs/design/implementation/transcript/README.md) | Record input in the history and bring it back | Implemented through transcript 001 |
| [`popup`](docs/design/implementation/popup/README.md) | Menu beside the pointer, and a button documentation line | Implemented through popup 000 |
| [`http`](docs/design/implementation/http/README.md) | GET requests, responses, and clickable JSON | Charter written, waiting for review |
| [`tutorial`](docs/design/implementation/tutorial/README.md) | A short tour of cards inside the listener | Charter written, waiting for review |

A new discussion should read [`AGENTS.md`](AGENTS.md). The listener,
listings, REPL, chips, SymPy, transcript, and popup specifications are
the law for the program as it stands. The HTTP and tutorial charters
are separate next explorations. The
[`transcript demo`](docs/design/implementation/transcript/demo.md) offers
examples to try.

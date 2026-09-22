# pbui

A terminal listener that keeps live objects in its history. Printed
names are presentations of files, directories, and processes. A click
hands the object to the next command.

Design for each exploration lives under
`docs/design/implementation/<name>/`: a charter, a spec, and a
`checkpoints/` folder. The program itself will live at this project
root. Create it, its environment, and its dependencies with uv only.
[`AGENTS.md`](AGENTS.md) is that rule.

| Exploration | What it is | Status |
|---|---|---|
| [`listener`](docs/design/implementation/listener/README.md) | First listener: `ls`, `ps`, `show`, `cd`, `rm`, `kill` | Charter written, waiting for review |

The designer conversation for this exploration reads
[`docs/design/implementation/listener/charter.md`](docs/design/implementation/listener/charter.md).
If you have been told to read that file, it is the whole assignment.

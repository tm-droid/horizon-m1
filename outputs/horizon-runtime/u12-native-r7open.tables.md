# Native shader comparison

Values are median [minimum, maximum] across valid rounds; a single round shows one value.
Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.

| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | b1-base | 1/1 | ref | 56.4 | 31.4 | n/a | 46.1 | 20.5 | 2667 | 3039 |  |
| makeup | b1-trial | 1/1 | ref | 54.0 | 27.2 | n/a | 40.7 | 24.1 | 2814 | 3135 |  |

Planned rounds skipped after a hopeless/unloaded result: 0.
Screenshot paths and per-pass timing lines are retained in the JSON results.

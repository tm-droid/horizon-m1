# Native shader comparison

Values are median [minimum, maximum] across valid rounds; a single round shows one value.
Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.

| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | cd-demand | 1/1 | ref | 52.7 | 31.7 | n/a | 41.6 | 18.3 | 2847 | 3195 |  |

Planned rounds skipped after a hopeless/unloaded result: 0.
Screenshot paths and per-pass timing lines are retained in the JSON results.

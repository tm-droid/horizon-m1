# Native shader comparison

Values are median [minimum, maximum] across valid rounds; a single round shows one value.
Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.

| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | cd-force | 1/1 | ref | 58.7 | 33.5 | n/a | 45.3 | 28.4 | 2734 | 3269 |  |
| makeup | cd-demand | 1/1 | ref | 56.0 | 33.5 | n/a | 44.5 | 16.4 | 2789 | 3197 |  |

Planned rounds skipped after a hopeless/unloaded result: 0.
Screenshot paths and per-pass timing lines are retained in the JSON results.

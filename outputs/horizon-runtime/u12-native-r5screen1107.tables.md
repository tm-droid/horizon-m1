# Native shader comparison

Values are median [minimum, maximum] across valid rounds; a single round shows one value.
Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.

| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | r5-v4-t | 1/1 | ref | 52.6 | 30.8 | n/a | 41.0 | 13.4 | 2696 | 2969 |  |
| n-daybreak020 | r5-v4-t | 1/1 | yes | 46.8 | 25.2 | -10.9 | 43.5 | 19.2 | 2601 | 2897 |  |

Planned rounds skipped after a hopeless/unloaded result: 0.
Screenshot paths and per-pass timing lines are retained in the JSON results.

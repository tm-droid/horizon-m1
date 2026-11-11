# Native shader comparison

Values are median [minimum, maximum] across valid rounds; a single round shows one value.
Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.

| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | r3-v4-t | 1/1 | ref | 57.3 | 32.5 | n/a | 45.4 | 23.9 | 2733 | 3495 |  |
| makeup-m1 | r3-v4-t | 1/1 | yes | 54.2 | 31.5 | -5.5 | 43.7 | 24.5 | 2789 | 3515 |  |

Planned rounds skipped after a hopeless/unloaded result: 0.
Screenshot paths and per-pass timing lines are retained in the JSON results.

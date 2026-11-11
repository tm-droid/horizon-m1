# Native shader comparison

Values are median [minimum, maximum] across valid rounds; a single round shows one value.
Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.

| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | r3-v4-t | 1/1 | ref | 58.5 | 34.1 | n/a | 48.1 | 29.8 | 2756 | 3693 |  |
| makeup-m1r2 | r3-v4-t | 1/1 | yes | 59.8 | 34.0 | 2.4 | 47.2 | 19.5 | 2810 | 3621 |  |

Planned rounds skipped after a hopeless/unloaded result: 0.
Screenshot paths and per-pass timing lines are retained in the JSON results.

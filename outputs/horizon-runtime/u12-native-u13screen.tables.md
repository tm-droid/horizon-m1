# Native shader comparison

Values are median [minimum, maximum] across valid rounds; a single round shows one value.
Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.

| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | r3-v4-t | 1/1 | ref | 53.1 | 27.9 | n/a | 39.4 | 19.6 | 2767 | 3310 |  |
| n-montarc | r3-v4-t | 1/1 | yes | 35.5 | 16.4 | -33.3 | 26.9 | 12.6 | 2683 | 3369 |  |
| n-montarc-m1 | r3-v4-t | 1/1 | yes | 49.3 | 23.3 | -7.2 | 39.3 | 14.3 | 2614 | 3418 |  |
| n-daybreak011 | r3-v4-t | 1/1 | yes | 47.3 | 22.7 | -10.9 | 42.8 | 15.2 | 2623 | 3403 |  |
| n-daybreak011-m1 | r3-v4-t | 1/1 | yes | 55.5 | 26.4 | 4.4 | 49.1 | 21.6 | 2631 | 3434 |  |

Planned rounds skipped after a hopeless/unloaded result: 0.
Screenshot paths and per-pass timing lines are retained in the JSON results.

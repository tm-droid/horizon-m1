# U12 native packs (r3 + v4, 1 round)

| case | ran | loaded | static avg | static 1% low | vs makeup avg | flight avg | flight 1% low | footprint peak MB | swap peak M | note |
|---|---|---|---|---|---|---|---|---|---|---|
| makeup | yes | ref | 19.9 | 11.8 | n/a | 16.3 | 9.8 | 2873 | 3632 |  |
| n-meridian | yes | True | 9.9 | 5.5 | -50.2% | 8.7 | 4.9 | 2845 | 3606 |  |
| n-meridian-compat | yes | True | 19.7 | 10.9 | -1.1% | 15.0 | 4.5 | 2504 | 3553 |  |
| n-daybreak011 | yes | True | 23.9 | 10.6 | +20.4% | 20.6 | 9.1 | 2663 | 3597 |  |
| n-daybreak020 | yes | False | 100.7 | 30.8 | +406.8% | 86.2 | 26.2 | 2186 | 3948 | shader pack daybreak-0.2.0.hshader refused: horizon-shaders.toml: TOML parse error at line 30, column 1 |
| n-montarc | yes | True | 18.2 | 10.3 | -8.6% | 15.7 | 9.1 | 2681 | 3835 |  |

scene.png: tests/u12-<case>-r3-v4-1/scene.png

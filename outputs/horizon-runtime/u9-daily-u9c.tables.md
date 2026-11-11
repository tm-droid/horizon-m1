## Auto-generated tables (u9c, finished 2026-11-06 19:42:56, complete=True, aborted=None)

Valid runs: 6 of 6 planned

| makeup static | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |
|---|---|---|---|---|---|---|---|---|
| avg fps | trim - daily | 3 | +6.12 | [+4.09, +7.70] | +5.97 | 19.86 | +30.8% | 3/3 |
| 1% low fps | trim - daily | 3 | +6.75 | [-0.01, +8.74] | +5.16 | 9.23 | +73.1% | 2/3 |
| p99 ms | trim - daily | 3 | -20.52 | [-39.23, -7.90] | -22.55 | 83.37 | -24.6% | 0/3 |
| GPU p99 ms | trim - daily | 3 | -15.30 | [-25.10, -2.58] | -14.33 | 61.35 | -24.9% | 0/3 |
| CPU p99 ms | trim - daily | 3 | -7.93 | [-36.92, +5.56] | -13.10 | 52.03 | -15.2% | 1/3 |

| makeup flight | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |
|---|---|---|---|---|---|---|---|---|
| avg fps | trim - daily | 3 | +4.87 | [+3.99, +4.91] | +4.59 | 16.53 | +29.5% | 3/3 |
| 1% low fps | trim - daily | 3 | +1.01 | [-0.62, +3.31] | +1.24 | 10.06 | +10.1% | 2/3 |
| p99 ms | trim - daily | 3 | -12.69 | [-30.71, +2.75] | -13.55 | 93.50 | -13.6% | 1/3 |
| GPU p99 ms | trim - daily | 3 | -14.15 | [-23.07, -13.21] | -16.81 | 75.44 | -18.8% | 0/3 |
| CPU p99 ms | trim - daily | 3 | -0.86 | [-15.49, +9.42] | -2.31 | 40.92 | -2.1% | 1/3 |

### Memory

| case | pair | n | footprint peak delta MB (median) | CI | RSS peak delta MB (median) | swap_peak delta M (median) |
|---|---|---|---|---|---|---|
| makeup | trim - daily | 3 | +31.0 | [-29.0, +159.0] | +158.6 | -6.0 |

### Visual (scene.png)

**makeup** mean abs gray diff per horizontal band (top to bottom), 0-255.

| comparison | band 1 | band 2 | band 3 | band 4 | band 5 | band 6 | verdict |
|---|---|---|---|---|---|---|---|
| same-arm spread (mean of within-arm pairs) | 9.41 | 4.34 | 6.14 | 4.42 | 5.64 | 6.38 | baseline |
| daily vs trim | 9.06 | 4.49 | 7.77 | 5.80 | 6.52 | 7.29 | within same-arm spread |

### Ore glow (v4 vs v3, r3 build)

no complete ore pair

### Per-run raw

| case | arm | round | static avg | static 1% | static p99 | static GPU p99 | flight avg | flight 1% | flight p99 | fp peak MB | swap Mbefore->after |
|---|---|---|---|---|---|---|---|---|---|---|---|
| makeup | daily | 1 | 19.1 | 8.2 | 99.4 | 72.9 | 16.0 | 8.7 | 107.3 | 2708 | 2960.38->3390.12 |
| makeup | daily | 2 | 19.9 | 11.5 | 83.4 | 61.3 | 16.7 | 10.1 | 93.5 | 2841 | 3215.88->3379.88 |
| makeup | daily | 3 | 20.0 | 9.2 | 73.9 | 58.9 | 16.5 | 10.6 | 85.8 | 2868 | 3211.88->3498.69 |
| makeup | trim | 1 | 25.2 | 15.0 | 60.2 | 47.8 | 20.9 | 12.0 | 76.6 | 2867 | 3246.12->3351.38 |
| makeup | trim | 2 | 23.9 | 11.5 | 75.5 | 58.8 | 20.7 | 11.1 | 80.8 | 2812 | 3143.31->3407.88 |
| makeup | trim | 3 | 27.7 | 18.0 | 53.4 | 43.6 | 21.4 | 10.0 | 88.6 | 2899 | 3490.69->3445.38 |

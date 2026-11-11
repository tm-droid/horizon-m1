# Clean r4 vs r3 paired comparison

Three paired rounds; identical trim/v4; booted Simulator shut down before this batch.

| makeup static | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |
|---|---|---|---|---|---|---|---|---|
| avg fps | candidate - r3 | 3 | +3.01 | [+0.88, +6.19] | +3.36 | 51.56 | +5.8% | 3/3 |
| 1% low fps | candidate - r3 | 3 | +1.65 | [-5.37, +6.51] | +0.93 | 30.27 | +5.5% | 2/3 |
| p99 ms | candidate - r3 | 3 | -1.53 | [-5.37, +3.51] | -1.13 | 31.37 | -4.9% | 1/3 |
| GPU p99 ms | candidate - r3 | 3 | -0.75 | [-2.82, -0.68] | -1.42 | 23.72 | -3.2% | 0/3 |
| CPU p99 ms | candidate - r3 | 3 | -0.38 | [-3.98, +6.45] | +0.70 | 11.53 | -3.3% | 1/3 |

| makeup flight | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |
|---|---|---|---|---|---|---|---|---|
| avg fps | candidate - r3 | 3 | +1.18 | [-4.82, +7.18] | +1.18 | 39.38 | +3.0% | 2/3 |
| 1% low fps | candidate - r3 | 3 | +1.07 | [-0.05, +4.86] | +1.96 | 20.97 | +5.1% | 2/3 |
| p99 ms | candidate - r3 | 3 | -0.90 | [-2.92, +2.59] | -0.41 | 42.86 | -2.1% | 1/3 |
| GPU p99 ms | candidate - r3 | 3 | +0.64 | [-6.52, +2.13] | -1.25 | 40.08 | +1.6% | 2/3 |
| CPU p99 ms | candidate - r3 | 3 | +0.65 | [+0.24, +1.01] | +0.63 | 10.23 | +6.4% | 3/3 |

| packs static | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |
|---|---|---|---|---|---|---|---|---|
| avg fps | candidate - r3 | 3 | +1.64 | [+1.27, +15.67] | +6.19 | 184.93 | +0.9% | 3/3 |
| 1% low fps | candidate - r3 | 3 | +2.12 | [+1.20, +2.82] | +2.05 | 56.48 | +3.7% | 3/3 |
| p99 ms | candidate - r3 | 3 | -0.51 | [-1.04, +0.19] | -0.45 | 16.21 | -3.1% | 1/3 |
| GPU p99 ms | candidate - r3 | 3 | +0.04 | [-0.39, +0.12] | -0.08 | 13.89 | +0.3% | 2/3 |
| CPU p99 ms | candidate - r3 | 3 | -0.71 | [-0.72, -0.25] | -0.56 | 4.42 | -16.1% | 0/3 |

| packs flight | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |
|---|---|---|---|---|---|---|---|---|
| avg fps | candidate - r3 | 3 | +1.22 | [-0.20, +9.73] | +3.58 | 150.98 | +0.8% | 2/3 |
| 1% low fps | candidate - r3 | 3 | +0.50 | [-2.13, +4.72] | +1.03 | 42.96 | +1.2% | 2/3 |
| p99 ms | candidate - r3 | 3 | -0.05 | [-1.18, +0.26] | -0.32 | 20.75 | -0.2% | 1/3 |
| GPU p99 ms | candidate - r3 | 3 | +0.54 | [-0.46, +0.84] | +0.30 | 18.14 | +3.0% | 2/3 |
| CPU p99 ms | candidate - r3 | 3 | -0.67 | [-2.11, -0.03] | -0.94 | 5.27 | -12.7% | 0/3 |

| case | pair | n | footprint peak delta MB (median) | CI | RSS peak delta MB (median) | swap_peak delta M (median) |
|---|---|---|---|---|---|---|
| makeup | candidate - r3 | 3 | +134.0 | [+36.0, +144.0] | -204.6 | +8.0 |
| packs | candidate - r3 | 3 | -60.0 | [-97.0, -3.0] | -67.7 | -8.0 |

**makeup** mean abs gray diff per horizontal band (top to bottom), 0-255.

| comparison | band 1 | band 2 | band 3 | band 4 | band 5 | band 6 | verdict |
|---|---|---|---|---|---|---|---|
| same-arm spread (mean of within-arm pairs) | 10.71 | 4.23 | 4.02 | 3.57 | 5.16 | 5.81 | baseline |
| candidate vs r3 | 9.06 | 3.58 | 3.76 | 3.33 | 4.67 | 5.04 | within same-arm spread |

**packs** mean abs gray diff per horizontal band (top to bottom), 0-255.

| comparison | band 1 | band 2 | band 3 | band 4 | band 5 | band 6 | verdict |
|---|---|---|---|---|---|---|---|
| same-arm spread (mean of within-arm pairs) | 0.00 | 0.00 | 2.02 | 1.17 | 0.04 | 0.00 | baseline |
| candidate vs r3 | 0.00 | 0.00 | 2.02 | 1.04 | 0.03 | 0.00 | within same-arm spread |


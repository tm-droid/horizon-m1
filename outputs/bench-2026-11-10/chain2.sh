#!/bin/zsh
cd ~/Developer/Horizon/outputs/bench-2026-11-10
python3 -I bench.py run --scenarios makeup --order D,S,R,R,S,D --tag a --start 10 > run-makeup-1.log 2>&1 || exit 3
python3 -I bench.py run --scenarios makeup --order S,R,D --tag a --start 16 > run-makeup-2.log 2>&1 || exit 4

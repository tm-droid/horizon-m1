import re, sys, collections
from pathlib import Path
L = Path(__file__).resolve().parent / "logs"


def norm(p):
    c = collections.Counter()
    for l in (L / p).read_text(errors="replace").splitlines():
        if "WARN" in l or "ERROR" in l:
            l = re.sub(r"^\[[0-9:]+\] ", "", l)
            l = re.sub(r"(custom entity model \w+): (no part|unknown target) [\w]+(\.\w+)?", r"\1: \2 X", l)
            c[l[:200]] += 1
    return c


a, b = norm("compat-STOCK-packno-latest.log"), norm("compat-DAILY-packyes-latest.log")
print("STOCK(no pack) WARN/ERROR lines:", sum(a.values()), "unique", len(a), "| DAILY(pack) lines:", sum(b.values()), "unique", len(b))
print("--- in STOCK(no pack) only (count)")
for k, v in sorted(a.items()):
    if k not in b:
        print(f"{v:3d} {k}")
print("--- in DAILY(pack) only (count)")
for k, v in sorted(b.items()):
    if k not in a:
        print(f"{v:3d} {k}")
print("--- in both")
for k in sorted(a):
    if k in b:
        print(f"{a[k]:3d}->{b[k]:3d} {k}")

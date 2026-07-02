"""
V64 patch — applied to NVH websiteV1/index.html.

Hero-section stats cards (rendered from the JS-escaped template string):
1. Replace the "£4.5M+ / In assets" stat with a "50+ / Cars" stat
   (counter counts to 50, no prefix/suffix, keeps the "+" superscript).
2. Change the "20+ / Properties" stat to an exact "22 / Properties"
   (counter counts to 22, "+" superscript removed per the exact count).

Both stats live once each in the escaped hero__stats markup; the script
asserts an exact single match before replacing, aborting otherwise.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "index.html")

# --- Stat 2: assets -> cars ---
STAT2_OLD = (
    '<div class=\\"hero__stat\\">\\n        '
    '<div class=\\"num\\"><span class=\\"hero-counter\\" '
    'data-target=\\"4.5\\" data-decimals=\\"1\\" data-prefix=\\"£\\" data-suffix=\\"M\\">'
    '£0.0M<\\/span><span class=\\"sup\\">+<\\/span><\\/div>\\n        '
    '<div class=\\"label\\">In assets<\\/div>'
)
STAT2_NEW = (
    '<div class=\\"hero__stat\\">\\n        '
    '<div class=\\"num\\"><span class=\\"hero-counter\\" '
    'data-target=\\"50\\" data-decimals=\\"0\\" data-prefix=\\"\\" data-suffix=\\"\\">'
    '0<\\/span><span class=\\"sup\\">+<\\/span><\\/div>\\n        '
    '<div class=\\"label\\">Cars<\\/div>'
)

# --- Stat 3: 20+ properties -> 22 properties (no "+") ---
STAT3_OLD = (
    '<div class=\\"hero__stat\\">\\n        '
    '<div class=\\"num\\"><span class=\\"hero-counter\\" '
    'data-target=\\"20\\" data-decimals=\\"0\\" data-prefix=\\"\\" data-suffix=\\"\\">'
    '0<\\/span><span class=\\"sup\\">+<\\/span><\\/div>\\n        '
    '<div class=\\"label\\">Properties<\\/div>'
)
STAT3_NEW = (
    '<div class=\\"hero__stat\\">\\n        '
    '<div class=\\"num\\"><span class=\\"hero-counter\\" '
    'data-target=\\"22\\" data-decimals=\\"0\\" data-prefix=\\"\\" data-suffix=\\"\\">'
    '0<\\/span><\\/div>\\n        '
    '<div class=\\"label\\">Properties<\\/div>'
)


def apply_once(html, label, old, new):
    n = html.count(old)
    if n != 1:
        print(f"ERROR: {label}: expected exactly 1 match, found {n}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] {label}: 1 match -> replacing")
    return html.replace(old, new, 1)


def main():
    with open(INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    html = apply_once(html, "Stat 2 (assets -> 50+ Cars)", STAT2_OLD, STAT2_NEW)
    html = apply_once(html, "Stat 3 (20+ -> 22 Properties)", STAT3_OLD, STAT3_NEW)

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Wrote {INDEX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

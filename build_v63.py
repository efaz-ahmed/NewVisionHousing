"""
V63 patch — applied to NVH websiteV1/index.html.

Changes:
1. UK map image swapped to the new Artifacts/UKMapLabelled.png
   (re-encodes the new PNG inline as base64 inside the .map-image src).
2. Sister-company CTA (Provision4Peace button) hover/focus state
   recoloured to the gold accent (--sage) with deep-green text for contrast,
   instead of the previous --rust-deep variant.
"""

import base64
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
NVH_DIR = os.path.dirname(ROOT)
INDEX = os.path.join(ROOT, "index.html")
NEW_MAP = os.path.join(NVH_DIR, "Artifacts", "UKMapLabelled.png")


def main() -> int:
    with open(NEW_MAP, "rb") as f:
        new_map_b64 = base64.b64encode(f.read()).decode("ascii")

    with open(INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    # --- 1. Replace UK map base64 inside the JS-escaped template string ---
    map_prefix = '<img class=\\"map-image\\" src=\\"data:image/png;base64,'
    start = html.find(map_prefix)
    if start < 0:
        print("ERROR: could not locate map-image src in index.html", file=sys.stderr)
        return 1
    payload_start = start + len(map_prefix)
    payload_end = html.find('\\"', payload_start)
    if payload_end < 0:
        print("ERROR: could not locate closing quote for map-image src", file=sys.stderr)
        return 1
    old_len = payload_end - payload_start
    html = html[:payload_start] + new_map_b64 + html[payload_end:]
    print(f"[OK] UK map base64 swapped: {old_len} -> {len(new_map_b64)} chars")

    # --- 2. Sister-company CTA hover/focus -> gold accent ---
    old_hover = (
        ".sister-cta-v23:hover,\\n"
        "  .sister-cta-v23:focus-visible {\\n"
        "    background: var(--rust-deep);\\n"
        "    transform: translateY(-1px);\\n"
        "    outline: none;\\n"
        "  }"
    )
    new_hover = (
        ".sister-cta-v23:hover,\\n"
        "  .sister-cta-v23:focus-visible,\\n"
        "  .sister-cta-v23:active {\\n"
        "    background: var(--sage);\\n"
        "    color: var(--rust);\\n"
        "    transform: translateY(-1px);\\n"
        "    outline: none;\\n"
        "  }"
    )
    if old_hover not in html:
        print("ERROR: could not locate sister-cta-v23 hover rule", file=sys.stderr)
        return 1
    html = html.replace(old_hover, new_hover, 1)
    print("[OK] Sister-company CTA hover/focus/active recoloured to gold accent (--sage)")

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Wrote {INDEX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

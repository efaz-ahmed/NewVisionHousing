"""
build_v61.py
============
Reduce the UK map size by 15% (relative to its current V58 size).

V58 set transform: scale(1.25). 15% smaller than that → 1.25 × 0.85
= 1.0625. Override the scale so the rendered map is small enough to
fit inside the card without clipping.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


PATCH_CSS = r"""
<style id="__nvh_v61_map_scale">
  /* V61: reduce UK map by 15% (1.25 × 0.85 = 1.0625). */
  @media (min-width: 769px) {
    .map-image {
      transform: scale(1.0625) !important;
      transform-origin: center center !important;
    }
  }
</style>
"""


def main() -> int:
    src_text = SRC.read_text(encoding="utf-8")
    tpl_re = re.compile(
        r'(<script type="__bundler/template">)(.+?)(</script>)',
        re.DOTALL,
    )
    m = tpl_re.search(src_text)
    open_tag, raw_json, close_tag = m.group(1), m.group(2), m.group(3)
    html = json.loads(raw_json)

    if "__nvh_v61_map_scale" in html:
        print("INFO: V61 already applied", file=sys.stderr)
        return 0

    html = html.replace("</head>", PATCH_CSS + "\n</head>", 1)
    print("   applied scale(1.0625) to .map-image (15% smaller than V58)")

    v61_marker = "\n<!-- V61: UK map -15% (scale 1.25 → 1.0625). -->\n"
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v61_marker + html[insert_at:]

    new_json = json.dumps(html, ensure_ascii=False).replace("</", r"<\/")
    out_text = (
        src_text[:m.start()]
        + open_tag
        + new_json
        + close_tag
        + src_text[m.end():]
    )

    DST.write_text(out_text, encoding="utf-8")
    delta = DST.stat().st_size - len(src_text)
    sign = "+" if delta >= 0 else ""
    print(
        f"OK: rewrote {DST.name} in place "
        f"({DST.stat().st_size:,} bytes, {sign}{delta:,} vs input)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

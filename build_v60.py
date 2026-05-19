"""
build_v60.py
============
The V58 scale(1.25) makes the map RENDER 25% larger but does not
change its layout box. The visual therefore extends beyond the
.core-card__visual cell, and that cell has `overflow: hidden`
(plus a constrained min-height) which clips the Swansea label at the
bottom of the card.

Fix at the container level (per user direction "make the container
bigger"):

1. `.core-card__visual { overflow: visible }` so the scaled image is
   not clipped by the card edge.
2. Increase the card cell's min-height at desktop so additional
   vertical space is reserved for the scaled map.
3. Slightly reduce horizontal padding on the visual cell so the
   .map-stage has more raw width to grow into.

No transforms are added or removed here; V58's scale(1.25) stays.
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
<style id="__nvh_v60_map_container">
  /* V60: enlarge the container that holds the UK map so V58's
     scale(1.25) renders fully without being clipped. */
  @media (min-width: 769px) {
    .core-card__visual {
      overflow: visible !important;
      padding-top: clamp(40px, 4vw, 72px) !important;
      padding-bottom: clamp(56px, 6vw, 96px) !important;
      padding-left: clamp(20px, 2.2vw, 36px) !important;
      padding-right: clamp(20px, 2.2vw, 36px) !important;
      min-height: 720px !important;
    }
    .core-card__visual .map-section,
    .core-card__visual .map-stage,
    .core-card__visual .map-emerge {
      overflow: visible !important;
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

    if "__nvh_v60_map_container" in html:
        print("INFO: V60 already applied", file=sys.stderr)
        return 0

    html = html.replace("</head>", PATCH_CSS + "\n</head>", 1)
    print("   applied container enlargement (overflow visible + min-height 720)")

    v60_marker = "\n<!-- V60: UK map container enlarged + overflow visible. -->\n"
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v60_marker + html[insert_at:]

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

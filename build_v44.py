"""
build_v44.py
============
In the "How becoming a shareholder works" card (Invest section), the
total summary `.invest-card--how .invest-total` is forced to a
horizontal row layout via:

    .invest-card--how .invest-total {
      flex-direction: row !important;
      align-items: center !important;
      ...
    }

That works on desktop where there's room next to £36,000 for the long
"Total commitment over ten years…" label. On mobile it crowds and
fights for width.

V44 flips just that container to `flex-direction: column` at <=640px,
so on phones £36,000 stacks at the top and the explanatory label sits
below it. Same content, no markup change, no impact on desktop.
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
<style id="__nvh_v44_invest_total_stack">
  /* V44: stack £36,000 above its label on mobile.
     The desktop rule (.invest-card--how .invest-total) uses
     !important to force a horizontal row -- our override matches
     selector + uses !important so source-order (later) wins. */
  @media (max-width: 640px) {
    .invest-card--how .invest-total {
      flex-direction: column !important;
      align-items: flex-start !important;
      gap: 10px !important;
    }
    /* Let the label take its natural full width below the figure */
    .invest-card--how .invest-total__label {
      flex: none !important;
      width: 100%;
    }
  }
</style>
"""


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: {SRC} not found", file=sys.stderr)
        return 1
    src_text = SRC.read_text(encoding="utf-8")
    tpl_re = re.compile(
        r'(<script type="__bundler/template">)(.+?)(</script>)',
        re.DOTALL,
    )
    m = tpl_re.search(src_text)
    if not m:
        print("ERROR: bundler template not found", file=sys.stderr)
        return 2

    open_tag, raw_json, close_tag = m.group(1), m.group(2), m.group(3)
    html = json.loads(raw_json)

    if "__nvh_v44_invest_total_stack" in html:
        print("ERROR: V44 already applied", file=sys.stderr)
        return 3

    html = html.replace("</head>", PATCH_CSS + "\n</head>", 1)

    v44_marker = (
        "\n<!-- V44: stack £36,000 figure above its label in the "
        "'How becoming a shareholder works' card on mobile (<=640px) -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v44_marker + html[insert_at:]

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

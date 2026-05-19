"""
build_v62.py
============
Swap the displayed identity (name + role + email + alt) of the two
founder cards in the team section: Syed Jushef Ali ↔ Abdul Kadir.

The image files in nvh_team_images_named/ are misnamed (the photo
file labelled "01_Syed_Jushef_Ali.webp" is in fact Abdul Kadir, and
"02_Abdul_Kadir.webp" is in fact Syed Jushef Ali), so the on-card
text needs to swap to match the real faces.

To keep each card self-consistent we swap all three identity fields
together using a sentinel-based 3-way exchange:
  * Display name  : "Syed Jushef Ali"            ↔ "Abdul Kadir"
  * Role label    : "Founder & Marketing Director"
                                                 ↔ "Founder & Managing Director"
  * Email address : "s.ali@nvhltd.com"           ↔ "a.kadir@nvhltd.com"

The image src attributes (the actual photo data URIs) stay where they
are, so each picture now sits beneath the correct name + role + email.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


PAIRS = [
    ("Syed Jushef Ali",               "Abdul Kadir"),
    ("Founder & Marketing Director",  "Founder & Managing Director"),
    ("s.ali@nvhltd.com",              "a.kadir@nvhltd.com"),
]


def swap_pair(text: str, a: str, b: str, sentinel: str) -> tuple[str, int]:
    """3-way swap of two literal strings in `text` using a sentinel."""
    n_a = text.count(a)
    n_b = text.count(b)
    text = text.replace(a, sentinel)
    text = text.replace(b, a)
    text = text.replace(sentinel, b)
    return text, n_a + n_b


def main() -> int:
    src_text = SRC.read_text(encoding="utf-8")
    tpl_re = re.compile(
        r'(<script type="__bundler/template">)(.+?)(</script>)',
        re.DOTALL,
    )
    m = tpl_re.search(src_text)
    open_tag, raw_json, close_tag = m.group(1), m.group(2), m.group(3)
    html = json.loads(raw_json)

    if "__nvh_v62_marker" in html:
        print("INFO: V62 already applied", file=sys.stderr)
        return 0

    for i, (a, b) in enumerate(PAIRS):
        html, total = swap_pair(html, a, b, f"__NVH_TMP_SWAP_{i}__")
        print(f"   swapped: {a!r} ↔ {b!r} (touched {total} occurrence(s))")

    v62_marker = (
        "\n<!-- V62: Syed Jushef Ali ↔ Abdul Kadir full identity swap "
        "(name + role + email) so each photo matches its real face. -->\n"
        '<style id="__nvh_v62_marker"></style>\n'
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v62_marker + html[insert_at:]

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

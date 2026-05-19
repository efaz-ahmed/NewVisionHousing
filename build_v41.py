"""
build_v41.py
============
TESTING swap: change the FormSubmit recipient address from
info@nvhltd.com to efaz.mintu@gmail.com so test submissions land in
the developer's inbox during QA.

For production rollout
----------------------
Swap back to info@nvhltd.com by re-running build_v40.py against the
current index.html (V40's recipient constant is the production one),
or run a V42 that flips the address the other way.

This file only touches two strings inside the bundler template's
`<script id="__nvh_form_submit_v2">` block:
  - the `RECIPIENT` JS constant
  - the safety-fallback email shown in the failure message
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"

OLD_EMAIL = "info@nvhltd.com"
NEW_EMAIL = "efaz.mintu@gmail.com"


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

    if NEW_EMAIL in html and OLD_EMAIL not in html:
        print(f"INFO: recipient already set to {NEW_EMAIL}; nothing to do",
              file=sys.stderr)
        return 0

    # Scope the replace to the V40 form-submit script block to avoid
    # accidentally touching unrelated references (e.g., the legacy
    # `mailto:info@nvhltd.com` link in the footer Contact column,
    # which should keep its public production address).
    block_re = re.compile(
        r'(<script id="__nvh_form_submit_v2">)(.*?)(</script>)',
        re.DOTALL,
    )
    block_m = block_re.search(html)
    if not block_m:
        print("ERROR: V40 form-submit script block not found", file=sys.stderr)
        return 3

    block_open, block_body, block_close = block_m.group(1), block_m.group(2), block_m.group(3)
    swaps = block_body.count(OLD_EMAIL)
    new_block_body = block_body.replace(OLD_EMAIL, NEW_EMAIL)
    print(f"   swapped {swaps} occurrence(s) of {OLD_EMAIL} -> {NEW_EMAIL}")
    if swaps == 0:
        print("WARN: no occurrences to swap inside V40 block", file=sys.stderr)

    html = (
        html[:block_m.start()]
        + block_open
        + new_block_body
        + block_close
        + html[block_m.end():]
    )

    v41_marker = (
        f"\n<!-- V41: TESTING -- contact form recipient swapped to {NEW_EMAIL} "
        f"(production address {OLD_EMAIL} kept in footer 'Contact' column). "
        "Run build_v40.py to restore production address. -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v41_marker + html[insert_at:]

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

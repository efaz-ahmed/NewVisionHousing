"""
build_v38.py
============
Static + polished marquee on mobile (regardless of motion preference).

Previous state
--------------
V37 made the marquee static ONLY under `prefers-reduced-motion: reduce`.
With motion enabled, the marquee still attempted a horizontal scroll
animation that — per the user's report — didn't actually move on
iPhone Chrome. The user's preference: keep the Quranic verse and its
English translation static + centered + polished on mobile, end of
story.

V38 fix
-------
At `<=768px`, force the marquee into a static centered caption block
regardless of `prefers-reduced-motion`:

  - Hide the 6 duplicated marquee items, keeping just the first
    Arabic/English pair (`:nth-child(n+3) { display: none }`)
  - Disable the scroll animation entirely
  - Drop the side/top fade gradient overlays (only useful when text
    is scrolling past them)
  - Drop the sage circular `::after` divider (only useful between
    items in a scrolling queue)
  - Reflow the track as a vertical column with the Arabic verse on
    top, English translation below
  - Polish typography:
      * Arabic — keep rust colour, tighten line-height, slight padding
      * English — italic, softer ink colour, narrower max-width for
        readable line length
  - Increase outer padding so the caption breathes inside its dark
    background band

Desktop (> 768px) is untouched.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


MARQUEE_CSS = r"""
<style id="__nvh_v38_marquee_mobile">
  /* ============================================================== */
  /*  V38: marquee as static centered caption on mobile             */
  /* ============================================================== */
  @media (max-width: 768px) {

    /* Calm the container; the inner caption now provides its own
       breathing room so the section padding can relax. */
    .marquee {
      padding: 36px 24px !important;
      overflow: visible !important;
    }

    /* Drop ALL fade overlays -- they exist to mask scrolling text
       at the edges; with static text they only add visual noise. */
    .marquee::before,
    .marquee::after {
      display: none !important;
    }
    .marquee-fade-top,
    .marquee-fade-bottom {
      display: none !important;
    }

    /* Reflow the track: kill the horizontal scroll, switch to a
       centered vertical column. */
    .marquee__track {
      animation: none !important;
      -webkit-animation: none !important;
      transform: none !important;
      -webkit-transform: none !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      gap: 18px !important;
      width: 100% !important;
      max-width: 100% !important;
      white-space: normal !important;
      text-align: center !important;
      will-change: auto;
    }

    /* Hide the 5 repeated copies (each pair is Arabic + English) --
       only the first pair stays visible. */
    .marquee__track > .marquee__item:nth-child(n+3) {
      display: none !important;
    }

    /* Item-level reset: no inline-flex (was for scroll gap layout),
       no trailing dot divider, centered + wrap-friendly. */
    .marquee__track .marquee__item {
      display: block !important;
      gap: 0 !important;
      text-align: center !important;
      white-space: normal !important;
      line-height: 1.5 !important;
      max-width: 38ch;
      margin: 0 auto !important;
      padding: 0 !important;
    }
    .marquee__track .marquee__item::after {
      display: none !important;
    }

    /* Arabic verse — keep rust accent, slightly larger and tighter. */
    .marquee__track .marquee__arabic {
      font-size: clamp(1.5rem, 5.5vw, 1.95rem) !important;
      line-height: 1.7 !important;
      color: var(--rust) !important;
      direction: rtl;
    }

    /* English translation — smaller, italic, softer ink for a clear
       hierarchy below the Arabic. */
    .marquee__track .marquee__item:not(.marquee__arabic) {
      font-size: 0.95rem !important;
      line-height: 1.55 !important;
      color: var(--ink-soft, #5a5a5a) !important;
      font-style: italic !important;
      font-family: var(--display) !important;
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

    if "__nvh_v38_marquee_mobile" in html:
        print("ERROR: V38 marquee fix already present", file=sys.stderr)
        return 3

    html = html.replace("</head>", MARQUEE_CSS + "\n</head>", 1)

    v38_marker = (
        "\n<!-- V38: marquee below hero is a static centered caption on "
        "mobile (no scroll, polished typography for Arabic verse + English "
        "translation) -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v38_marker + html[insert_at:]

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

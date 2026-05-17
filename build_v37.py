"""
build_v37.py
============
Fixes two content-visibility bugs that only appear when the user has
`prefers-reduced-motion: reduce` enabled (common on iPhones running
Low Power Mode, or anyone with Settings -> Accessibility -> Motion ->
Reduce Motion turned on).

============================================================
Bug 1 — Closing journey text "The next milestone is yours." invisible
============================================================
Root cause: the closing-line words have an initial CSS state of
`opacity: 0; transform: translateY(40px)`. A class `.is-revealed`
triggers a `nvh-word-rise` keyframe that animates them to visible.
The class is added by an IntersectionObserver inside `initJourney()`
(GSAP block). At line ~5764 the function early-returns when
reduce-motion is on:

    var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

So the `.is-revealed` class is NEVER added under reduce-motion and
the words stay at opacity 0 forever. Content failure.

Fix: a `@media (prefers-reduced-motion: reduce)` CSS rule that forces
the words to opacity 1 + transform none + animation none. No JS
change needed; the content just shows statically when motion is off.

============================================================
Bug 2 — Marquee not animating on iPhone
============================================================
Root cause: at line ~3082 the page has a global a11y reset:

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        ...
      }
    }

This crushes the marquee's 45s scroll animation to 10 microseconds --
runs once instantly then sits at translate3d(0,0,0). User sees a
static block of 12 repeated Arabic+English copies stacked next to
each other -- visually broken (the marquee was designed for one
visible item at a time as text scrolls past).

Fix: under reduce-motion, hide the duplicate copies and centre a
SINGLE pair (Arabic verse + English translation) statically. The
marquee container becomes a calm centred caption instead of a frozen
horizontal queue.

Both fixes go into a `@media (prefers-reduced-motion: reduce)` block
inside a new `<style id="__nvh_ios_v3_motion">` so they survive the
documentElement swap and don't interfere with the page when motion
is enabled.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


MOTION_CSS = r"""
<style id="__nvh_ios_v3_motion">
  /* ========================================================== */
  /*  V37: reduce-motion content visibility                     */
  /* ========================================================== */
  @media (prefers-reduced-motion: reduce) {

    /* ----- FIX 1: closing journey line shows statically ----- */
    /* The JS that adds `.is-revealed` early-returns under
       reduce-motion, leaving the words at opacity 0 forever.
       Force the final state so the line is always visible. */
    #journey .journey__closing-word {
      opacity: 1 !important;
      transform: none !important;
      animation: none !important;
    }
    #journey .journey__closing-yours {
      transform: none !important;
      animation: none !important;
    }
    /* Defensive: in case any `.is-revealed` keyframe still fires,
       its animation-fill-mode shouldn't override our visible state. */
    #journey .journey__closing-word.is-revealed {
      opacity: 1 !important;
      transform: none !important;
    }

    /* ----- FIX 2: marquee renders as a static centred caption -- */
    /* The global `* { animation-duration: 0.01ms !important }`
       reset stops the marquee scroll. Without the scroll, the 6
       duplicated copies pile up next to each other -- visually
       broken. Hide the duplicates and centre the first pair. */
    .marquee {
      overflow: visible !important;
    }
    .marquee__track {
      animation: none !important;
      -webkit-animation: none !important;
      transform: none !important;
      -webkit-transform: none !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      gap: 8px !important;
      width: 100% !important;
      text-align: center !important;
      white-space: normal !important;
    }
    /* Show ONLY the first Arabic + English pair; hide all repeats. */
    .marquee__track .marquee__item {
      white-space: normal !important;
      text-align: center !important;
    }
    .marquee__track .marquee__item:nth-child(n+3) {
      display: none !important;
    }
    /* Fade overlays were meant to mask the marquee's edges as text
       scrolled past them. With static text they obscure the
       (now-fixed) words -- hide them. */
    .marquee-fade-top,
    .marquee-fade-bottom {
      display: none !important;
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

    if "__nvh_ios_v3_motion" in html:
        print("ERROR: V37 motion fix already present", file=sys.stderr)
        return 3

    html = html.replace("</head>", MOTION_CSS + "\n</head>", 1)

    v37_marker = (
        "\n<!-- V37: reduce-motion content visibility -- journey closing line "
        "shows statically (not invisible at opacity 0), marquee renders as a "
        "static centred caption (not a frozen horizontal queue) -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v37_marker + html[insert_at:]

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

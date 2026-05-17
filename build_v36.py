"""
build_v36.py
============
iOS-Chrome / iOS-Safari production-readiness fixes.

Reads index.html, applies the patches below in-place, writes back to
index.html.

============================================================
Issue 1 — Links/buttons not tappable on iPhone (Chrome + Safari)
============================================================
Root cause: `.nav-drawer-overlay` has:
    display: none;
    position: fixed; inset: 0;
    z-index: 98;
    opacity: 0;
    transition: opacity .4s var(--ease);
And at <=1080px:
    @media (max-width: 1080px) {
      .nav-drawer-overlay { display: block; }
    }
So on mobile the overlay is present in the layout (display: block),
INVISIBLE (opacity: 0), but with the default `pointer-events: auto` and
`position: fixed; inset: 0` covering the entire viewport at z-index 98.
Every tap goes to the overlay first and is consumed -- the link
beneath never receives the click. Desktop (> 1080px) escapes because
display: none removes the overlay from the layout entirely.

Fix: `.nav-drawer-overlay { pointer-events: none }` by default, and
flip to `pointer-events: auto` ONLY when `.open` is set (i.e. when the
drawer is actually open and the overlay IS the modal backdrop).

============================================================
Issue 2 — Tapping text on iPhone selects a whole section
============================================================
Root cause: iOS Safari/Chrome's tap-and-hold heuristic upgrades the
selection target to the nearest "block-like" ancestor when:
  - the tapped element has no explicit `user-select` declaration, OR
  - any ancestor has `cursor: pointer` / a click handler.
The page leaves `user-select` at its default (which iOS interprets
liberally for text-on-images, text-inside-flex containers, etc.).

Fix: explicitly mark text-bearing elements as `user-select: text` so
iOS keeps the selection at the text-node level, not the container.
Apply `-webkit-touch-callout: default` so long-press behaves naturally.

============================================================
Issue 3 — Marquee not animating on iPhone
============================================================
Root cause candidates (most likely → least):
  a) The user's iPhone has Reduce Motion enabled in Settings →
     Accessibility → Motion. The `@media (prefers-reduced-motion: reduce)`
     block in the bundle disables the animation.
  b) iOS Safari pauses CSS animations on elements that are off-screen
     when `will-change` isn't declared, to save battery.
  c) `transform` repaints can lag without GPU acceleration hints.

Fix: declare `will-change: transform` + an explicit `translate3d` start
state to promote the marquee track to its own compositor layer (iOS
keeps GPU-promoted animations running off-screen). Reduce-motion is a
genuine accessibility preference -- we respect it; if the user opts in
to motion, the animation will play.

============================================================
Bonus iOS polish
============================================================
- `html { -webkit-text-size-adjust: 100% }` -- iOS Safari in landscape
  sometimes auto-enlarges text; this disables that for design control.
- All fixes injected as a single `<style id="__nvh_ios_v2">` block in
  the bundler template so they live through the documentElement swap.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


IOS_V2_CSS = r"""
<style id="__nvh_ios_v2">
  /* ========================================================== */
  /*  V36: iOS production-readiness fixes                       */
  /* ========================================================== */

  /* ----- FIX 1: nav-drawer-overlay click blocker ------------ */
  /* The overlay is `display: block` at <=1080px (so its opacity
     transition can play) but with default `pointer-events: auto`
     it was swallowing every tap below it on mobile. Disable
     pointer-events whenever the drawer is closed. */
  .nav-drawer-overlay {
    pointer-events: none !important;
  }
  .nav-drawer-overlay.open {
    pointer-events: auto !important;
  }

  /* ----- FIX 2: iOS text selection grabbing whole sections -- */
  /* Explicitly declare text-bearing elements as `user-select: text`
     and allow normal long-press callout. iOS's heuristic that
     upgrades selection to a block-level ancestor only kicks in
     when these are unset, so being explicit pins the selection
     to the text run. */
  p, h1, h2, h3, h4, h5, h6, span, li, blockquote, em, strong, a,
  figcaption, dt, dd, label, time, address, q, cite {
    -webkit-user-select: text;
            user-select: text;
    -webkit-touch-callout: default;
  }
  /* Re-disable on actual buttons / interactive controls -- selecting
     button labels by tap-and-hold isn't useful and was never desired. */
  button, button *, .btn-primary, .btn-ghost,
  .nav__cta, .nav__cta *, .nav-drawer__cta, .nav-drawer__cta *,
  .menu-toggle, .menu-toggle * {
    -webkit-user-select: none;
            user-select: none;
    -webkit-touch-callout: none;
  }

  /* ----- FIX 3: marquee animation GPU-layer hint ------------ */
  /* Without `will-change`, iOS Safari can pause CSS animations on
     elements that are scrolled out of view, which means the marquee
     visibly "skips" or sits still when you scroll back to it.
     `will-change: transform` plus an explicit translate3d start
     state promotes the track to its own composited layer so iOS
     keeps the animation alive in the background. */
  .marquee__track {
    will-change: transform;
    -webkit-transform: translate3d(0, 0, 0);
            transform: translate3d(0, 0, 0);
    -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
  }

  /* ----- Bonus polish: iOS text auto-zoom in landscape ------ */
  html {
    -webkit-text-size-adjust: 100%;
            text-size-adjust: 100%;
  }

  /* ----- Bonus polish: avoid iOS form-input zoom (V35 already)
     and ensure -webkit-appearance reset doesn't strip submit
     button styling that we rely on. Reaffirm here for clarity. */
  input[type="submit"],
  input[type="button"],
  button.invest-form__submit {
    -webkit-appearance: none;
            appearance: none;
    /* Restore cursor for buttons we just neutered */
    cursor: pointer;
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

    if "__nvh_ios_v2" in html:
        print("ERROR: V36 iOS-v2 fix already present", file=sys.stderr)
        return 3

    html = html.replace("</head>", IOS_V2_CSS + "\n</head>", 1)

    v36_marker = (
        "\n<!-- V36: iOS production fixes -- nav-drawer-overlay pointer-events "
        "(unblocks tap), user-select: text on text content (selection no longer "
        "grabs whole sections), marquee will-change + translate3d (animation "
        "doesn't pause off-screen on iOS), text-size-adjust 100% (no auto-enlarge "
        "in landscape) -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v36_marker + html[insert_at:]

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

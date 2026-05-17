"""
build_v35.py
============
Reads index.html (the current head) and applies four targeted fixes
in-place. Writes back to index.html.

Fixes
-----
1. UK map mis-centred inside Core Holdings card.
   A legacy desktop rule `.map-stage { transform: translateX(-6%) !important }`
   was outranking V34's `transform: none` (no !important). The map sat
   ~18px left of the column's centre. V34's `__nvh_mobile` block now
   uses !important on transform / clip-path / opacity for the inner
   wrappers so the legacy desktop rule is beaten on mobile.

2. iOS Safari input auto-zoom on focus.
   Form inputs were `font-size: 0.9rem` / `0.95rem` (~14-15px). iOS
   auto-zooms when an input < 16px is focused, then never zooms back.
   At <=768px we bump every form-input font-size to 16px so iOS leaves
   the zoom alone.

3. Bundler-template viewport missing `viewport-fit=cover`.
   The outer static HTML has the right viewport, but the bundler swap
   replaces the entire document, so the template's viewport wins. On
   iPhones with a notch / Dynamic Island / home indicator, content
   was not rendering into the safe areas. Patched the template's
   <meta name="viewport"> to match the outer one.

4. Universal touch-tap polish for iOS.
   Adds `-webkit-tap-highlight-color: transparent` so the default
   grey flash on tap is suppressed, and `-webkit-appearance: none`
   on buttons + inputs so iOS doesn't apply rounded native chrome.

All four fixes injected as a single `<style id="__nvh_ios">` block in
the bundler template (so they survive the documentElement swap and
apply both pre- and post-swap).
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"   # in-place modify


IOS_CSS = r"""
<style id="__nvh_ios">
  /* V35 FIX 1 — Map alignment.
     Force `transform: none` on the inner map wrappers with !important
     so the legacy desktop rule `.map-stage { transform: translateX(-6%) !important }`
     elsewhere in the bundle stops shifting the map ~18px to the left
     of its column's centre on mobile.
     (V34's same selectors were missing !important on transform; the
     consolidated block treats this as the canonical fix.) */
  @media (max-width: 900px) {
    .core-card__visual .map-section,
    .core-card__visual .map-stage,
    .core-card__visual .map-emerge {
      transform: none !important;
      -webkit-transform: none !important;
    }
  }

  /* V35 FIX 2 — iOS Safari input auto-zoom prevention.
     Any input with font-size < 16px triggers a forced zoom on focus
     in iOS Safari (and Chrome on iPhone, which uses the same engine).
     Bump every form-input + textarea to 16px on phones. The legacy
     0.95rem (~15.2px) was just under the threshold. */
  @media (max-width: 768px) {
    .invest-form input,
    .invest-form textarea,
    .invest-form select,
    .invest-form--application input,
    .invest-form--application textarea,
    .invest-form--application select,
    .invest-form--pill input,
    .invest-form--pill textarea {
      font-size: 16px !important;
    }
  }

  /* V35 FIX 4 — iOS touch polish.
     `-webkit-tap-highlight-color: transparent` removes the default
     grey flash on tap; `-webkit-appearance: none` on buttons + inputs
     prevents iOS from applying default native chrome (rounded corners,
     inset shadows). Globally safe -- desktop browsers ignore these. */
  * {
    -webkit-tap-highlight-color: transparent;
  }
  button,
  input[type="button"],
  input[type="submit"],
  input[type="reset"],
  input[type="text"],
  input[type="email"],
  input[type="tel"],
  input[type="number"],
  input[type="search"],
  input[type="url"],
  textarea,
  select {
    -webkit-appearance: none;
    appearance: none;
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

    if "__nvh_ios" in html:
        print("ERROR: V35 iOS fix already present", file=sys.stderr)
        return 3

    # --- Fix 3: viewport in the bundler template ----------------------- #
    # Outer HTML's viewport already has viewport-fit=cover; the template's
    # doesn't, and after the swap the template wins. Match them.
    old_vp = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    new_vp = '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    if old_vp in html:
        html = html.replace(old_vp, new_vp, 1)
        print("   updated template <meta viewport> with viewport-fit=cover")
    else:
        print("WARN: template viewport meta not found / already updated",
              file=sys.stderr)

    # --- Fixes 1, 2, 4: inject the new <style> block ------------------- #
    html = html.replace("</head>", IOS_CSS + "\n</head>", 1)

    v35_marker = "\n<!-- V35: iOS optimisation -- map alignment !important, input font-size 16px (no auto-zoom), viewport-fit=cover, tap-highlight transparent, appearance reset -->\n"
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v35_marker + html[insert_at:]

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

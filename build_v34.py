"""
build_v34.py
============
Consolidation pass. NO new features.

Reads IndexV33.html. Removes the seven layered mobile style blocks
(__nvh_v24_mobile, _v25_mobile, _v26_mobile, _v27_mobile, _v28_mobile,
_v29_mobile, _v32_drawer_cta) and the timer-based __nvh_v28_map_clear
script. Replaces them with:

  - ONE consolidated <style id="__nvh_mobile">                 (one block, one cascade)
  - ONE MutationObserver-based <script id="__nvh_map_clear">  (no setTimeouts, no resize listener)

The consolidated CSS:
  - keeps ONLY the winning declaration for each property/selector
    pair (V26's frosted-card rules, for example, are dropped entirely
    because V27 cancelled every one of them)
  - drops `!important` everywhere it is no longer needed (i.e. where
    no other layer is competing for the same property)
  - replaces the V29 `min-height: calc(min(100vw - 60px, 520px) * 1.293 + 100px)`
    magic number with an explicit `aspect-ratio: 1038 / 1343` on the
    map image, so the visual region naturally sizes to the image
  - keeps the same media-query breakpoints so behaviour is byte-for-
    byte identical to V33 at every viewport width

The consolidated JS:
  - early-returns on viewports > 900px
  - uses MutationObserver instead of setTimeout(0, 600, 1800) +
    resize listener -- when GSAP writes inline styles to .map-emerge,
    the observer fires and clears them immediately, with no polling

The V31 preloader fix lives in the OUTER static HTML (outside the
bundler template) so it is untouched by this consolidation.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "IndexV33.html"
DST = HERE / "index.html"


# Style block ids to STRIP from the template (in order of removal).
# These are all superseded by the new consolidated block below.
STRIP_STYLE_IDS = [
    "__nvh_v24_mobile",
    "__nvh_v25_mobile",
    "__nvh_v26_mobile",
    "__nvh_v27_mobile",
    "__nvh_v28_mobile",
    "__nvh_v29_mobile",
    "__nvh_v32_drawer_cta",
]

# Script block ids to STRIP and replace.
STRIP_SCRIPT_IDS = [
    "__nvh_v28_map_clear",
]

# V-marker comments to strip (HTML comments documenting the now-removed
# layers). Anchored to specific text so we don't touch other comments.
STRIP_COMMENTS = [
    "<!-- V29: extend core-holdings visual min-height to viewport-scaled calc so map never crops -->",
    "<!-- V28: mobile (hero stats +40%, BG -20% more, core-holdings card resized for full map) -->",
    "<!-- V27: mobile (no frosted card, single-row stats, 2-line +35% h1, bg -40%, portfolio map order + crop fix) -->",
    "<!-- V26: hero stats legibility (frosted card + bold tracked text) -->",
    "<!-- V25: mobile follow-up (hero body+btn bold, grounded image centred & +30%) -->",
    "<!-- V24: mobile compatibility pass (hamburger JS, hero left-crop fix, hero center+bold, nav CTA hidden on mobile, flagship image hidden on mobile) -->",
    "<!-- V32: hero stat 150->200, Become a Shareholder -> #get-in-touch, drawer link styled as button -->",
    "<!-- V28: ensure core-holdings map renders fully on mobile -->",
]


# --------------------------------------------------------------------------- #
# CONSOLIDATED MOBILE CSS
# --------------------------------------------------------------------------- #
# Organisation:
#   1.  Top nav (>=1080px hides drawer, <=1080px hides top-bar CTA)
#   2.  Hero -- background + headline + subhead + buttons + stats
#   3.  Belief section -- grounded-in-principle image
#   4.  Portfolio -- core holdings card layout + UK map sizing
#   5.  Vision/Upcoming -- hide flagship image on mobile
#   6.  Drawer CTA -- the pill button "Become a Shareholder"
#
# Breakpoints used:
#   <=1080px : nav-only changes (drawer takes over)
#   <=900px  : core holdings card switches to vertical stack
#   <=768px  : hero BG image fix + flagship image hidden
#   <=640px  : hero typography overhaul (centred, bold, +35%)
CONSOLIDATED_CSS = r"""
<style id="__nvh_mobile">
  /* ============================================================== */
  /*  CONSOLIDATED MOBILE STYLES (replaces __nvh_v24..v32 blocks)   */
  /* ============================================================== */

  /* ----- Default state (always applied) ----- */
  /* Hero h1 has parallel desktop + mobile line variants in the markup
     (added in V27 to allow a 2-line wrap on phones without rewriting
     the desktop slide-up animation). Hide the mobile variant by
     default; show it only at <=640px (further down). */
  .hero h1 .line--mobile { display: none; }

  /* Drawer "Become a Shareholder" pill button. Specificity
     `.nav-drawer a.nav-drawer__cta` = (0,0,3,1) cleanly outranks the
     base `.nav-drawer a` = (0,0,1,1) rule, so no !important needed. */
  .nav-drawer a.nav-drawer__cta {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.55em;
    width: 100%;
    box-sizing: border-box;
    margin-top: 18px;
    padding: 14px 24px;
    background: var(--emerald, #0F3D34);
    color: var(--cream, #F5EEDE);
    border-bottom: none;
    border-radius: 999px;
    font-family: var(--sans);
    font-weight: 600;
    font-size: 0.98rem;
    letter-spacing: 0.02em;
    text-align: center;
    text-decoration: none;
    transition: background 0.25s ease, transform 0.25s ease;
  }
  .nav-drawer a.nav-drawer__cta:hover,
  .nav-drawer a.nav-drawer__cta:focus-visible {
    background: var(--emerald-deep, #0A2D24);
    color: var(--cream, #F5EEDE);
    transform: translateY(-1px);
    outline: none;
  }
  .nav-drawer a.nav-drawer__cta .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--rust, #b34c3a);
    display: inline-block;
    flex-shrink: 0;
  }

  /* ----- Tablet + phone: nav drawer takes over ----- */
  @media (max-width: 1080px) {
    /* Top-bar "Become a Shareholder" hidden; same link lives in the drawer */
    .nav__cta { display: none !important; }
  }

  /* ----- Tablet + phone: portfolio Core Holdings vertical stack ----- */
  @media (max-width: 900px) {
    .wire-card--core {
      padding-bottom: 16px;
    }
    /* Switch the layout from grid to plain block stacking. With both
       children being flex items, the base CSS's `flex: 0 1 auto` was
       collapsing the visual column below the image's natural height.
       Block layout removes the flex sizing dance entirely. */
    .core-card__layout {
      display: block !important;
      grid-template-columns: 1fr;
      min-height: 0;
      height: auto;
    }
    .core-card__content {
      order: 0;
      width: 100%;
      box-sizing: border-box;
    }
    /* The visual region (UK map) needs an explicit min-height because
       `aspect-ratio` on the inner <img> sizes the image but does NOT
       propagate up to the parent box -- the parent would otherwise
       collapse to the layout's flex-resolved height and leave the
       image overflowing visibly outside its container.
       The fraction `1343 / 1038` is the image's intrinsic height /
       width -- self-documenting (vs the old `* 1.293` magic constant).
       The 520px cap mirrors the .map-image `max-width: 520px` below.
       The +100px adds room for the 36px top + 52px bottom padding
       plus a small breathing margin so the box always fits. */
    #portfolio .core-card__visual {
      padding: 36px 18px 52px;
      margin-top: 8px;
      border-top: 1px solid var(--hairline, rgba(0, 0, 0, 0.12));
      border-left: 0;
      border-bottom: 0;
      overflow: visible;
      width: 100%;
      box-sizing: border-box;
      height: auto;
      display: block;
      min-height: calc(min(100vw - 60px, 520px) * (1343 / 1038) + 100px);
    }
    /* All inner wrappers: block layout, no clipping. The clip-path
       and opacity resets defend against GSAP writing inline styles
       that would otherwise leave the map invisible or cropped. The
       JS map-clear observer below this style block tracks future
       inline-style mutations and clears them reactively.
       `transform: none !important` is required to beat a legacy
       desktop rule `.map-stage { transform: translateX(-6%) !important }`
       elsewhere in the bundle that otherwise shifts the map ~18px
       to the left of the column's centre. */
    .core-card__visual .map-section,
    .core-card__visual .map-stage,
    .core-card__visual .map-emerge {
      display: block;
      overflow: visible;
      height: auto;
      max-height: none;
      width: 100%;
      max-width: 100%;
      min-height: 0;
      clip-path: none !important;
      -webkit-clip-path: none !important;
      transform: none !important;
      opacity: 1 !important;
    }
    /* Map image -- aspect-ratio drives intrinsic height so the
       container can size from it without a calc() magic number. */
    .core-card__visual .map-image {
      display: block;
      width: 100%;
      max-width: 520px;
      height: auto;
      margin: 0 auto;
      aspect-ratio: 1038 / 1343;
    }
  }

  /* ----- Phone: hero background + flagship image hidden ----- */
  @media (max-width: 768px) {
    /* Hero background -- neutralise desktop's `translateX(96px)` +
       `-12px` horizontal bleed (which left the LEFT edge uncovered
       once the headline centres on phones) and dim to 0.4 opacity so
       the bone overlay reads through more strongly. */
    .hero__bg-wrap {
      left: 0 !important;
      right: 0 !important;
      animation: none !important;
    }
    .hero__bg-img {
      transform: none !important;
      object-position: center center !important;
      opacity: 0.4 !important;
    }
    /* Strip the V26 frosted card on .hero__stats -- the simple
       hairline-top border looks calmer over the dimmed BG. */
    .hero__stats {
      background: none !important;
      -webkit-backdrop-filter: none !important;
      backdrop-filter: none !important;
      border: none !important;
      border-top: 1px solid var(--hairline) !important;
      box-shadow: none !important;
      padding: 22px 0 0 !important;
      border-radius: 0 !important;
    }
    /* Flagship "Grand Occasions" image hidden -- copy column carries
       the meaning on phones. */
    .upcoming-wireframe__cell--visual {
      display: none !important;
    }
    .upcoming-wireframe__grid {
      grid-template-columns: 1fr !important;
    }
  }

  /* ----- Phone (small): hero typography centred + bold + larger ---- */
  @media (max-width: 640px) {
    /* Hero column -- centred, symmetric padding */
    .hero {
      justify-content: center;
    }
    .hero__content {
      text-align: center !important;
      align-items: center !important;
      padding-left: 24px !important;
      padding-right: 24px !important;
      display: flex;
      flex-direction: column;
    }
    /* Hero headline -- switch to 2-line mobile variant + bold + +35% */
    .hero h1 .line--desktop { display: none !important; }
    .hero h1 .line--mobile  { display: block !important; }
    .hero h1,
    .hero h1 .word {
      font-weight: 700 !important;
      text-align: center !important;
    }
    .hero h1 {
      font-size: clamp(3.3rem, 2.1rem + 4.3vw, 5.2rem) !important;
      line-height: 0.98 !important;
    }
    /* Subhead -- centred, bolder, narrower max-width for readability */
    .hero__sub {
      text-align: center !important;
      font-weight: 700 !important;
      max-width: 38ch !important;
      margin-left: auto !important;
      margin-right: auto !important;
    }
    /* Buttons -- centred, both bold */
    .hero__actions {
      justify-content: center !important;
      align-items: center !important;
      width: 100% !important;
    }
    .hero__actions .btn-primary,
    .hero__actions .btn-ghost {
      font-weight: 700 !important;
    }
    /* Stats -- single row of 3 columns with +40% font + tracked label.
       !important required to outrank the V23 base rule
       `@media (max-width: 560px) { .hero__stats { grid-template-columns: repeat(2, 1fr) !important; } }`
       that would otherwise force 2 columns at small phone widths. */
    .hero__stats {
      grid-template-columns: repeat(3, 1fr) !important;
      gap: 8px !important;
      max-width: 100% !important;
    }
    .hero__stat {
      text-align: center !important;
    }
    .hero__stat .num {
      font-size: clamp(1.96rem, 7.3vw, 2.6rem) !important;
      letter-spacing: -0.02em !important;
    }
    .hero__stat .label {
      font-size: 0.87rem !important;
      letter-spacing: 0.10em !important;
      margin-top: 8px !important;
      line-height: 1.2 !important;
    }
    /* Belief section -- "Grounded in principle" image centred and
       ~30% larger than the base clamp would produce on phones. */
    .grounded-heading {
      text-align: center;
      display: flex;
      justify-content: center;
    }
    .grounded-roots-img {
      width: min(90vw, 416px) !important;
      max-width: 90vw !important;
      margin-left: auto !important;
      margin-right: auto !important;
      display: block !important;
    }
  }
</style>
"""


# --------------------------------------------------------------------------- #
# CONSOLIDATED MAP-CLEAR SCRIPT
# --------------------------------------------------------------------------- #
# Replaces __nvh_v28_map_clear which used setTimeout(0, 600, 1800) +
# resize listener to undo GSAP's inline styles. The MutationObserver
# version watches the elements and reactively clears any inline style
# write -- no polling, no race, no repeated work.
CONSOLIDATED_JS = r"""
<!-- Consolidated map-clear: MutationObserver replaces setTimeout polling -->
<script id="__nvh_map_clear">
  (function () {
    if (window.__nvh_map_clear_init) return;
    window.__nvh_map_clear_init = true;

    // Only needed on the mobile path where we override the desktop
    // wipe-up. On desktop GSAP's inline styles power the reveal
    // animation and must be left alone.
    if (!window.matchMedia('(max-width: 900px)').matches) return;

    function clearMapStyles(el) {
      el.style.removeProperty('clip-path');
      el.style.removeProperty('-webkit-clip-path');
      el.style.removeProperty('transform');
      el.style.removeProperty('opacity');
      el.style.removeProperty('min-height');
      el.style.removeProperty('height');
      el.style.removeProperty('max-height');
    }

    function attach() {
      var els = document.querySelectorAll(
        '.core-card__visual .map-emerge, ' +
        '.core-card__visual .map-stage, ' +
        '.core-card__visual .map-section'
      );
      if (!els.length) return false;

      els.forEach(clearMapStyles);

      // Reactive guard: if GSAP (or anything else) writes inline
      // styles after our first clear, the observer fires and the
      // styles are removed immediately. No polling, no race.
      var obs = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          if (mutations[i].attributeName === 'style') {
            clearMapStyles(mutations[i].target);
          }
        }
      });
      els.forEach(function (el) {
        obs.observe(el, { attributes: true, attributeFilter: ['style'] });
      });
      return true;
    }

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      setTimeout(attach, 0);
    } else {
      window.addEventListener('DOMContentLoaded', attach);
    }
  })();
</script>
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

    if "__nvh_mobile" in html and "id=\"__nvh_mobile\"" in html:
        print("ERROR: __nvh_mobile (consolidated) already present", file=sys.stderr)
        return 3

    # --- Strip layered style blocks ------------------------------------- #
    stripped_styles = 0
    for sid in STRIP_STYLE_IDS:
        block_re = re.compile(
            r'\s*<style id="' + re.escape(sid) + r'"[^>]*>.*?</style>',
            re.DOTALL,
        )
        new_html, n = block_re.subn("", html, count=1)
        if n != 1:
            print(f"WARN: <style id='{sid}'> not found / not removed", file=sys.stderr)
        else:
            stripped_styles += 1
            html = new_html
    print(f"   stripped {stripped_styles}/{len(STRIP_STYLE_IDS)} layered <style> blocks")

    # --- Strip layered script blocks ------------------------------------ #
    stripped_scripts = 0
    for sid in STRIP_SCRIPT_IDS:
        block_re = re.compile(
            r'\s*<!--[^>]*?-->\s*<script id="' + re.escape(sid) + r'"[^>]*>.*?</script>',
            re.DOTALL,
        )
        new_html, n = block_re.subn("", html, count=1)
        if n != 1:
            # Try without the leading comment
            block_re = re.compile(
                r'\s*<script id="' + re.escape(sid) + r'"[^>]*>.*?</script>',
                re.DOTALL,
            )
            new_html, n = block_re.subn("", html, count=1)
        if n != 1:
            print(f"WARN: <script id='{sid}'> not found / not removed", file=sys.stderr)
        else:
            stripped_scripts += 1
            html = new_html
    print(f"   stripped {stripped_scripts}/{len(STRIP_SCRIPT_IDS)} layered <script> blocks")

    # --- Strip V-marker comments that documented the now-removed layers - #
    stripped_comments = 0
    for c in STRIP_COMMENTS:
        if c in html:
            html = html.replace(c + "\n", "", 1)
            html = html.replace(c, "", 1) if c in html else html
            stripped_comments += 1
    print(f"   stripped {stripped_comments}/{len(STRIP_COMMENTS)} V-marker comments")

    # --- Inject consolidated style + script ----------------------------- #
    html = html.replace("</head>", CONSOLIDATED_CSS + "\n</head>", 1)
    html = html.replace("</body>", CONSOLIDATED_JS + "\n</body>", 1)

    # --- V34 marker ----------------------------------------------------- #
    v34_marker = "\n<!-- V34: consolidation pass -- single __nvh_mobile style block + __nvh_map_clear observer (replaces v24..v29, v32) -->\n"
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v34_marker + html[insert_at:]

    # --- Re-encode and write -------------------------------------------- #
    new_json = json.dumps(html, ensure_ascii=False).replace("</", r"<\/")
    out_text = (
        src_text[:m.start()]
        + open_tag
        + new_json
        + close_tag
        + src_text[m.end():]
    )

    DST.write_text(out_text, encoding="utf-8")
    delta = DST.stat().st_size - SRC.stat().st_size
    sign = "+" if delta >= 0 else ""
    print(
        f"OK: wrote {DST.name} "
        f"({DST.stat().st_size:,} bytes, {sign}{delta:,} vs V33)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

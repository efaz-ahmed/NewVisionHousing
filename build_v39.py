"""
build_v39.py
============
Two changes:

1. Hero "Invest with us" CTA re-pointed from `#partnership` to
   `#get-in-touch`. The other Become-a-Shareholder anchors (top nav,
   drawer, footer) already target #get-in-touch from V32; the hero's
   primary button was the lone holdout.

2. Get-in-touch form now submits via mailto: to info@nvhltd.com.
   The existing onsubmit handler only changed the button text -- the
   form never actually delivered anywhere. V39 replaces it with a
   script that:
     - reads every form field via FormData
     - constructs a subject line ("NVH Shareholder Enquiry - <name>")
     - builds a labelled, multi-line plain-text body
     - opens the user's default email client with mailto:info@nvhltd.com
       pre-filled (subject + body URL-encoded)
     - updates the button text to confirm

   The mailto: approach is zero-dependency and works on every device
   that has a mail client (iOS Mail, Gmail, Outlook, etc.). If the
   user later wants server-side delivery (no mail-client step), the
   handler can be swapped for a Formspree / Netlify Forms / EmailJS
   POST -- the form markup itself doesn't change.

Both changes are inside the bundler template.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


# Script attached to the form. Lives in the bundler template so it
# re-attaches after the documentElement swap.
FORM_SUBMIT_JS = r"""
<!-- V39: Get-in-touch form -> mailto:info@nvhltd.com -->
<script id="__nvh_form_submit">
  (function () {
    if (window.__nvh_form_submit_init) return;
    window.__nvh_form_submit_init = true;

    var RECIPIENT = 'info@nvhltd.com';
    var SUBJECT_PREFIX = 'NVH Shareholder Enquiry';

    function attach() {
      var form = document.querySelector('.invest-form--application');
      if (!form) return false;

      // Defensive: if any inline onsubmit lingered we want our handler
      // to run alone, so we strip the attribute. (build_v39.py also
      // removes it in the source, this is just belt-and-braces.)
      form.removeAttribute('onsubmit');

      form.addEventListener('submit', function (e) {
        e.preventDefault();

        var fd = new FormData(form);
        var name  = (fd.get('fullName') || '').toString().trim();
        var email = (fd.get('email')    || '').toString().trim();
        var phone = (fd.get('phone')    || '').toString().trim();
        var loc   = (fd.get('location') || '').toString().trim();
        var msg   = (fd.get('message')  || '').toString().trim();

        var subject = SUBJECT_PREFIX + (name ? ' — ' + name : '');
        var bodyLines = [
          'Full name: ' + name,
          'Email: '     + email,
          'Phone: '     + phone,
          'Location: '  + loc,
          '',
          'Message:',
          msg,
          '',
          '—',
          'Sent via the New Vision Housing contact form'
        ];
        var body = bodyLines.join('\n');

        var mailto = 'mailto:' + RECIPIENT
                   + '?subject=' + encodeURIComponent(subject)
                   + '&body='    + encodeURIComponent(body);

        // Open the user's mail client. window.location.href works on
        // every mobile + desktop browser. iOS opens Mail (or default
        // mail app); Android opens Gmail (or default); desktop opens
        // the registered mailto: handler.
        window.location.href = mailto;

        var btn = form.querySelector('.invest-form__submit');
        if (btn) {
          btn.textContent = 'Opening your email…';
          setTimeout(function () {
            btn.textContent = 'Thank you, we will be in touch.';
          }, 1500);
        }
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

    if "__nvh_form_submit" in html:
        print("ERROR: V39 form submit script already present",
              file=sys.stderr)
        return 3

    # --- Change 1: re-point hero "Invest with us" -> #get-in-touch ---- #
    hero_btn_old = '<a href="#partnership" class="btn-primary">'
    hero_btn_new = '<a href="#get-in-touch" class="btn-primary">'
    if hero_btn_old in html:
        html = html.replace(hero_btn_old, hero_btn_new, 1)
        print('   re-pointed hero btn-primary -> #get-in-touch')
    else:
        print("WARN: hero btn-primary anchor not found / already #get-in-touch",
              file=sys.stderr)

    # --- Change 2a: strip the inline onsubmit (button-text-only handler) -- #
    # Original markup line:
    #   <form class="invest-form invest-form--application" onsubmit="event.preventDefault(); this.querySelector('.invest-form__submit').textContent = 'Thank you, we will be in touch.';">
    old_form_open = (
        '<form class="invest-form invest-form--application" '
        'onsubmit="event.preventDefault(); this.querySelector(\'.invest-form__submit\').textContent = \'Thank you, we will be in touch.\';">'
    )
    new_form_open = '<form class="invest-form invest-form--application">'
    if old_form_open in html:
        html = html.replace(old_form_open, new_form_open, 1)
        print("   stripped inline onsubmit from contact form")
    else:
        print("WARN: contact form's inline onsubmit not found at expected position",
              file=sys.stderr)

    # --- Change 2b: inject mailto-attaching script before </body> ----- #
    html = html.replace("</body>", FORM_SUBMIT_JS + "\n</body>", 1)

    # --- V39 marker --------------------------------------------------- #
    v39_marker = (
        "\n<!-- V39: hero 'Invest with us' -> #get-in-touch; contact form "
        "submits via mailto:info@nvhltd.com (replaces the inline button-"
        "text-only onsubmit handler) -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v39_marker + html[insert_at:]

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

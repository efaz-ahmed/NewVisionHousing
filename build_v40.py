"""
build_v40.py
============
Replaces V39's mailto: form handler with a server-side delivery flow
via FormSubmit.co (https://formsubmit.co).

Why FormSubmit.co
-----------------
- No account required, no API key, no signup
- POST to `https://formsubmit.co/ajax/<recipient>` -> email arrives
  at the recipient address
- Free, JSON AJAX endpoint with CORS
- Spam protection out of the box
- One-time activation: the first submission triggers an activation
  email to info@nvhltd.com that the owner must click; from that
  point onward every submission delivers automatically without any
  further interaction

User experience now
-------------------
1. User fills the form
2. Clicks Submit
3. Button shows "Sending..."
4. Email arrives at info@nvhltd.com (no mail client opens)
5. Form clears + button shows "Thank you, we will be in touch."

Failure handling
----------------
If the fetch fails (offline, rate-limited, FormSubmit downtime), the
button switches to "Couldn't send — please email us at info@nvhltd.com"
and re-enables for retry. We don't auto-fall-back to mailto: because
that would re-introduce the very mail-client UX the user wants to
avoid; instead we surface a clear failure message with a contact
address.

V40 strips the V39 mailto: handler entirely and injects the FormSubmit
script in its place.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


RECIPIENT = "info@nvhltd.com"


FORM_SUBMIT_JS = r"""
<!-- V40: Contact form -> FormSubmit.co AJAX -> email at info@nvhltd.com -->
<script id="__nvh_form_submit_v2">
  (function () {
    if (window.__nvh_form_submit_v2_init) return;
    window.__nvh_form_submit_v2_init = true;

    // The recipient address. FormSubmit will forward every form
    // submission to this email. The first POST after deployment
    // triggers a one-time activation email -- click the link in
    // it once and all subsequent submissions deliver automatically.
    var RECIPIENT = '__RECIPIENT__';
    var ENDPOINT = 'https://formsubmit.co/ajax/' + RECIPIENT;
    var SUBJECT_PREFIX = 'NVH Shareholder Enquiry';

    function attach() {
      var form = document.querySelector('.invest-form--application');
      if (!form) return false;

      // Defensive: in case any earlier handler (V39 mailto: inline)
      // is still attached, strip the attribute so it can't race ours.
      form.removeAttribute('onsubmit');

      var btn = form.querySelector('.invest-form__submit');
      var ORIGINAL_LABEL = btn ? btn.textContent : 'Show Interest';

      function setBtn(text, disabled) {
        if (!btn) return;
        btn.textContent = text;
        btn.disabled = !!disabled;
      }

      function resetBtnAfter(ms, label) {
        setTimeout(function () {
          setBtn(label || ORIGINAL_LABEL, false);
        }, ms);
      }

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (btn && btn.disabled) return;

        var fd = new FormData(form);
        var name  = (fd.get('fullName') || '').toString().trim();
        var email = (fd.get('email')    || '').toString().trim();
        var phone = (fd.get('phone')    || '').toString().trim();
        var loc   = (fd.get('location') || '').toString().trim();
        var msg   = (fd.get('message')  || '').toString().trim();

        // FormSubmit accepts arbitrary keys -- they become labelled
        // rows in the email body. Reserved keys (prefixed `_`) tune
        // the email formatting + behaviour:
        //   _subject  -> email subject line
        //   _template -> 'table' renders fields as an HTML table
        //   _captcha  -> 'false' disables the captcha (we still have
        //                 honeypot protection via _honey)
        //   _honey    -> hidden field; if filled, treated as spam
        var payload = {
          'Full name': name,
          'Email':     email,
          'Phone':     phone,
          'Location':  loc,
          'Message':   msg,
          '_subject':  SUBJECT_PREFIX + (name ? ' — ' + name : ''),
          '_template': 'table',
          '_captcha':  'false',
          '_honey':    ''       // populated only by bots
        };

        setBtn('Sending…', true);

        fetch(ENDPOINT, {
          method:  'POST',
          mode:    'cors',
          headers: {
            'Content-Type': 'application/json',
            'Accept':       'application/json'
          },
          body: JSON.stringify(payload)
        }).then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        }).then(function (data) {
          // FormSubmit returns `{success: "true"}` on success.
          var ok = data && (data.success === 'true' || data.success === true);
          if (!ok) throw new Error(data && data.message || 'Unknown error');
          form.reset();
          setBtn('Thank you, we will be in touch.', true);
          resetBtnAfter(6000);
        }).catch(function (err) {
          // Surface a clear failure -- we deliberately do NOT fall back
          // to mailto: because the whole point of V40 is to avoid the
          // mail-client UX. The user can retry, or copy the email
          // address that appears in the message.
          try { console.error('[NVH form] submission failed:', err); } catch (e) {}
          setBtn('Couldn’t send — please email ' + RECIPIENT, false);
        });
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
""".replace("__RECIPIENT__", RECIPIENT)


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

    if "__nvh_form_submit_v2" in html:
        print("ERROR: V40 form submit (v2) already present", file=sys.stderr)
        return 3

    # --- Strip the V39 mailto: script block ----------------------------- #
    v39_re = re.compile(
        r'\s*<!--[^>]*?-->\s*<script id="__nvh_form_submit"[^>]*>.*?</script>',
        re.DOTALL,
    )
    new_html, n = v39_re.subn("", html, count=1)
    if n != 1:
        # Try without the leading comment, in case it was stripped earlier
        v39_re2 = re.compile(
            r'\s*<script id="__nvh_form_submit"[^>]*>.*?</script>',
            re.DOTALL,
        )
        new_html, n = v39_re2.subn("", html, count=1)
    if n != 1:
        print("WARN: V39 mailto: script not found / not removed",
              file=sys.stderr)
    else:
        html = new_html
        print("   stripped V39 mailto: handler script")

    # --- Inject the V40 FormSubmit AJAX script before </body> ---------- #
    html = html.replace("</body>", FORM_SUBMIT_JS + "\n</body>", 1)

    # --- V40 marker comment -------------------------------------------- #
    v40_marker = (
        "\n<!-- V40: contact form delivers via FormSubmit.co AJAX -> "
        "info@nvhltd.com. No mail client. Owner must click the one-time "
        "activation email FormSubmit sends after the first submission, "
        "then all future submissions deliver automatically. -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v40_marker + html[insert_at:]

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

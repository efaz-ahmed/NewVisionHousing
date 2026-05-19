"""
build_v43.py
============
Swaps the contact form's submission endpoint from FormSubmit (V42,
currently down) to a same-origin Vercel serverless function at
`/api/contact`. The function (api/contact.js) delivers via Resend.

Why this works where V42 didn't
-------------------------------
- `/api/contact` is the same origin as the site, so there's no CORS
  preflight, no cross-origin failure mode, no "Failed to fetch" from
  third-party service outages.
- The serverless function handles all email-service interaction
  server-side; if Resend has an outage we control the error message
  and could swap to any other provider in minutes.
- The API key lives in Vercel env vars, never in client-visible code.

What this script does
---------------------
1. Strips the V42 `__nvh_form_submit_v3` script block (the failing
   FormSubmit one).
2. Injects a new `__nvh_form_submit_v4` script that POSTs JSON to
   `/api/contact` with the form fields, then shows the success /
   failure UI exactly as before.

The new script keeps:
- file:// origin detection (still useful for local QA without a server)
- detailed console logging on failure
- in-UI honest error message

But removes:
- All FormSubmit-specific fields (_subject, _template, _captcha,
  _honey was kept as a generic honeypot the server now checks)
- All third-party endpoint URLs (everything is same-origin now)
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


NEW_SCRIPT = r"""
<!-- V43: Contact form -> /api/contact (Vercel serverless + Resend) -->
<script id="__nvh_form_submit_v4">
  (function () {
    if (window.__nvh_form_submit_v4_init) return;
    window.__nvh_form_submit_v4_init = true;

    // Same-origin endpoint. Vercel routes /api/contact to the
    // serverless function at api/contact.js in this repo.
    var ENDPOINT = '/api/contact';
    var IS_FILE_ORIGIN = location.protocol === 'file:';

    function attach() {
      var form = document.querySelector('.invest-form--application');
      if (!form) return false;

      // Strip stale handlers from earlier versions
      form.removeAttribute('onsubmit');

      var btn = form.querySelector('.invest-form__submit');
      var ORIGINAL_LABEL = btn ? btn.textContent : 'Show Interest';

      function setBtn(text, disabled) {
        if (!btn) return;
        btn.textContent = text;
        btn.disabled = !!disabled;
      }

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (btn && btn.disabled) return;

        // file:// origin can't reach a Vercel function unless we have
        // a local dev server (`vercel dev`). Plain `python -m http.server`
        // serves the static files but doesn't run the function. Tell
        // the user what to expect.
        if (IS_FILE_ORIGIN) {
          setBtn('Open via a web server to submit', false);
          try { console.warn('[NVH form] file:// origin -- /api/contact needs Vercel (or `vercel dev`) to respond.'); } catch (err) {}
          return;
        }

        var fd = new FormData(form);
        var payload = {
          fullName: (fd.get('fullName') || '').toString().trim(),
          email:    (fd.get('email')    || '').toString().trim(),
          phone:    (fd.get('phone')    || '').toString().trim(),
          location: (fd.get('location') || '').toString().trim(),
          message:  (fd.get('message')  || '').toString().trim(),
          _honey:   ''   // populated only by bots; server discards if filled
        };

        setBtn('Sending…', true);

        fetch(ENDPOINT, {
          method: 'POST',
          headers: {
            'Accept':       'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        }).then(function (res) {
          return res.text().then(function (raw) {
            try { console.log('[NVH form] response', res.status, raw); } catch (e) {}
            var data = {};
            try { data = raw ? JSON.parse(raw) : {}; } catch (e) {
              throw new Error('Server sent non-JSON: ' + raw.slice(0, 120));
            }
            if (!res.ok || data.success !== true) {
              var msg = (data && data.message) ? data.message : ('HTTP ' + res.status);
              throw new Error(msg);
            }
            return data;
          });
        }).then(function () {
          form.reset();
          setBtn('Thank you, we will be in touch.', true);
          setTimeout(function () { setBtn(ORIGINAL_LABEL, false); }, 8000);
        }).catch(function (err) {
          try { console.error('[NVH form] submission failed:', err); } catch (e) {}
          var short = (err && err.message) ? err.message : 'Network error';
          if (short.length > 90) short = short.slice(0, 90) + '…';
          setBtn('Couldn’t send: ' + short, false);
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

    if "__nvh_form_submit_v4" in html:
        print("ERROR: V43 form submit (v4) already present", file=sys.stderr)
        return 3

    # Strip the V42 FormSubmit script
    v42_re = re.compile(
        r'\s*<!--[^>]*?-->\s*<script id="__nvh_form_submit_v3"[^>]*>.*?</script>',
        re.DOTALL,
    )
    new_html, n = v42_re.subn("", html, count=1)
    if n != 1:
        v42_re2 = re.compile(
            r'\s*<script id="__nvh_form_submit_v3"[^>]*>.*?</script>',
            re.DOTALL,
        )
        new_html, n = v42_re2.subn("", html, count=1)
    if n != 1:
        print("WARN: V42 FormSubmit script not found / not removed",
              file=sys.stderr)
    else:
        html = new_html
        print("   stripped V42 FormSubmit fetch handler")

    # Inject the V43 Vercel-API fetch script
    html = html.replace("</body>", NEW_SCRIPT + "\n</body>", 1)

    v43_marker = (
        "\n<!-- V43: contact form POSTs to /api/contact (Vercel serverless "
        "function backed by Resend). Same-origin so no CORS. Email "
        "service-side, recipient + API key via env vars. -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v43_marker + html[insert_at:]

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

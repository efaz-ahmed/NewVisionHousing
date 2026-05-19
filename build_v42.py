"""
build_v42.py
============
Fix "Couldn't send" error from V40/V41 form submission.

Likely root cause
-----------------
V40 sent the FormSubmit POST with `Content-Type: application/json`.
That triggers a CORS preflight (OPTIONS request) before the actual
POST. FormSubmit's CORS configuration sometimes drops the preflight
response, which means the browser blocks the POST entirely and the
fetch promise rejects -- exactly the symptom the user reported.

Switching the body to `URLSearchParams` (which fetch sends as
`application/x-www-form-urlencoded`) avoids the preflight entirely:
that content-type is on the CORS "simple request" allowlist, so the
browser sends the POST directly without an OPTIONS round-trip.
FormSubmit accepts URL-encoded payloads identically to JSON ones --
the same `_subject`, `_template`, etc. fields work.

Bonus fixes in V42
------------------
- Detailed console logging: status code + response body on every
  failure so we can diagnose the real cause if anything else breaks.
- Honest in-UI failure: shows the actual error message (truncated)
  so the user can screenshot it for debugging.
- Detects `file://` origin and shows a clear message instead of a
  cryptic CORS error -- the form CANNOT work via file:// (CORS
  blocks any cross-origin fetch from a null origin). Local testing
  needs an HTTP server, e.g. `python -m http.server 8765`.
- First-submission hint: if FormSubmit returns `success === 'false'`,
  the message points the user toward the activation email.

V42 replaces the V40 script entirely.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
DST = HERE / "index.html"


# Read whatever recipient is currently in the V40 script (V41 may have
# swapped it for testing). The build extracts the existing value.
def extract_current_recipient(html: str) -> str:
    m = re.search(r"var RECIPIENT = '([^']+)';", html)
    if m:
        return m.group(1)
    return "info@nvhltd.com"


def make_v42_script(recipient: str) -> str:
    return (
        r"""
<!-- V42: Contact form -> FormSubmit (URL-encoded, no CORS preflight) -->
<script id="__nvh_form_submit_v3">
  (function () {
    if (window.__nvh_form_submit_v3_init) return;
    window.__nvh_form_submit_v3_init = true;

    var RECIPIENT = '__RECIPIENT__';
    var ENDPOINT = 'https://formsubmit.co/ajax/' + RECIPIENT;
    var SUBJECT_PREFIX = 'NVH Shareholder Enquiry';
    var IS_FILE_ORIGIN = location.protocol === 'file:';

    function attach() {
      var form = document.querySelector('.invest-form--application');
      if (!form) return false;

      // Strip any stale handlers left by V39/V40
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

        // file:// origin will always fail CORS. Tell the user clearly
        // rather than letting them watch a cryptic network error.
        if (IS_FILE_ORIGIN) {
          setBtn('Open via a web server (not file://) to submit', false);
          try { console.warn('[NVH form] file:// origin -- CORS blocks the submission. Use a local HTTP server (e.g. python -m http.server) or deploy.'); } catch (err) {}
          return;
        }

        var fd = new FormData(form);

        // URLSearchParams body -> sent as application/x-www-form-urlencoded,
        // which is on the CORS "simple request" allowlist so the browser
        // does NOT send a preflight OPTIONS request. JSON body triggered
        // a preflight that FormSubmit's CORS sometimes dropped, which
        // was causing the V40 "Couldn't send" failure.
        var params = new URLSearchParams();
        params.append('Full name', (fd.get('fullName') || '').toString().trim());
        params.append('Email',     (fd.get('email')    || '').toString().trim());
        params.append('Phone',     (fd.get('phone')    || '').toString().trim());
        params.append('Location',  (fd.get('location') || '').toString().trim());
        params.append('Message',   (fd.get('message')  || '').toString().trim());
        // FormSubmit reserved fields
        var name = (fd.get('fullName') || '').toString().trim();
        params.append('_subject',  SUBJECT_PREFIX + (name ? ' — ' + name : ''));
        params.append('_template', 'table');
        params.append('_captcha',  'false');
        params.append('_honey',    '');     // spam honeypot

        setBtn('Sending…', true);

        fetch(ENDPOINT, {
          method: 'POST',
          mode:   'cors',
          headers: { 'Accept': 'application/json' },
          body:   params.toString()
        }).then(function (res) {
          // Read body as text first so we can log even non-JSON responses
          return res.text().then(function (raw) {
            try { console.log('[NVH form] response', res.status, raw); } catch (e) {}
            if (!res.ok) {
              throw new Error('HTTP ' + res.status + (raw ? ' — ' + raw.slice(0, 120) : ''));
            }
            var data = {};
            try { data = raw ? JSON.parse(raw) : {}; } catch (e) {
              throw new Error('Non-JSON response: ' + raw.slice(0, 120));
            }
            var ok = data && (data.success === 'true' || data.success === true);
            if (!ok) {
              var msg = (data && data.message) ? data.message : 'Unknown server error';
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
          // Show the real error -- helps diagnose issues like
          // "needs activation", rate-limit, network down, etc.
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
""".replace("__RECIPIENT__", recipient)
    )


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

    if "__nvh_form_submit_v3" in html:
        print("ERROR: V42 form submit (v3) already present", file=sys.stderr)
        return 3

    # Preserve whatever recipient is currently active (V41 may have set
    # the testing address). V42 doesn't change the recipient, only the
    # transport.
    recipient = extract_current_recipient(html)
    print(f"   preserving current recipient: {recipient}")

    # --- Strip the V40 script (the failing one) ----------------------- #
    v40_re = re.compile(
        r'\s*<!--[^>]*?-->\s*<script id="__nvh_form_submit_v2"[^>]*>.*?</script>',
        re.DOTALL,
    )
    new_html, n = v40_re.subn("", html, count=1)
    if n != 1:
        v40_re2 = re.compile(
            r'\s*<script id="__nvh_form_submit_v2"[^>]*>.*?</script>',
            re.DOTALL,
        )
        new_html, n = v40_re2.subn("", html, count=1)
    if n != 1:
        print("WARN: V40 form-submit script not found / not removed",
              file=sys.stderr)
    else:
        html = new_html
        print("   stripped V40 JSON-fetch form handler")

    # --- Inject the V42 URL-encoded script ---------------------------- #
    html = html.replace("</body>", make_v42_script(recipient) + "\n</body>", 1)

    # --- V42 marker --------------------------------------------------- #
    v42_marker = (
        "\n<!-- V42: contact form fetch now sends URL-encoded body "
        "(no CORS preflight); detailed error reporting in UI + console; "
        "file:// origin detected and reported clearly -->\n"
    )
    head_idx = html.find("<head>")
    if head_idx != -1:
        insert_at = head_idx + len("<head>")
        html = html[:insert_at] + v42_marker + html[insert_at:]

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
